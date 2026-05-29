# Asynchronous Title Generation

## Problem

Starting a chat from `home-page.tsx` feels slow because title generation blocks the
critical path before the LLM ever runs:

1. `HomePage.startChat` → `POST /sessions` (`createSession`).
2. `SessionService.create` (`session_service.py:32`) **awaits** `title_generator.generate(...)`
   — a full LLM round-trip — *before* the session row is created and the response returns.
3. Only after that does the client navigate to `/chat/:id` and start the message SSE stream
   (`useChatSession` effect → `streamSendMessage`).

So the user waits for two sequential LLM calls (title, then first agent inference) before
seeing anything.

## Goal

- `POST /sessions` returns **immediately** with a session that has no title yet (empty title =
  "pending").
- The assistant inference SSE stream starts right away (unchanged trigger).
- The title is generated **concurrently** with the first agent run and pushed down the *same*
  SSE message stream as a new event, so the first message feels instant.
- While the title is pending, the UI shows a **skeleton** (chat header + sidebar item); it is
  swapped for the real title the moment the `session.title_generated` event arrives.

## Key architectural constraint (read before coding)

The Dishka `SessionRepository` is `Scope.REQUEST` and wraps a single SQLAlchemy `AsyncSession`.
**An `AsyncSession` is not safe for concurrent use.** Therefore we must **not** run a second
coroutine that mutates the `Session` aggregate and calls `repository.save()` while the agent
loop is also persisting.

Decision: the title **LLM call** (which touches no DB) runs as a concurrent `asyncio.Task`,
but applying the result to the domain aggregate, persisting it, and emitting the SSE event all
happen **in the main generator coroutine** (the one already yielding agent events). This keeps
all DB access single-threaded while still overlapping the title LLM latency with the agent
inference.

---

## Backend changes

### 1. Stop blocking session creation on the title — `application/session_service.py`

- In `create(...)`, remove the `await self._title_generator.generate(...)` call. Create the
  session with an empty title (the "pending" sentinel):

  ```python
  @timed()
  async def create(self, *, owner_id: UUID, initial_prompt: str) -> Session:
      session = Session(title="", entries=[], owner_id=owner_id)
      return await self._session_repository.create(session=session)
  ```

  (`initial_prompt` is still accepted for signature/route compatibility; it is now consumed by
  the first `send_message` instead. Keep the param.)
- Remove the now-unused `title_generator` constructor dependency from `SessionService` and its
  imports. (It moves to `SessionConversationService` — step 3.)

### 2. New application event — `application/events.py`

Add a dataclass and include it in the `SessionEvent` union:

```python
@dataclass(frozen=True)
class SessionTitleGenerated:
    title: str
```

Add `SessionTitleGenerated` to the `type SessionEvent = (...)` union and export it from
`application/__init__.py` (the SSE mapper imports event types from there).

### 3. Generate the title inside the conversation flow — `application/conversation_service.py`

- Inject `SessionTitleGenerator` into `SessionConversationService.__init__` (new param
  `title_generator`), store as `self._title_generator`.
- In `send_message(...)`, after `session.add_user_message(...)`, decide whether a title is
  still needed and kick off the LLM task concurrently:

  ```python
  title_task = self._maybe_start_title_generation(session=session, prompt=content)
  async for event in self._persist_and_resume_agent(
      session=session,
      resolved_tool_call=resolved_tool_call,
      title_task=title_task,
  ):
      yield event
  ```

  ```python
  def _maybe_start_title_generation(
      self, *, session: Session, prompt: str
  ) -> asyncio.Task[str] | None:
      if session.title.strip():        # already has a title → nothing to do
          return None
      return asyncio.create_task(self._title_generator.generate(initial_prompt=prompt))
  ```

  Using "empty title" as the trigger means only the first message of a freshly created session
  generates a title; `answer_follow_ups` / `skip_remaining_follow_ups` pass `title_task=None`.

- Thread `title_task` through `_persist_and_resume_agent` and interleave a single title emission
  into `_run_agent_and_consume_user_curation_events`. Interleaving pattern (emit as soon as the
  task is done, otherwise flush at the end):

  ```python
  async def _persist_and_resume_agent(self, *, session, resolved_tool_call=None, title_task=None):
      await self._persist_session(session=session)
      for event in self._to_tool_call_resolution_events(resolved_tool_call):
          yield event
      try:
          async for event in self._run_agent_and_consume_user_curation_events(session=session):
              yield event
              for title_event in await self._emit_title_if_ready(session, title_task):
                  yield title_event
          for title_event in await self._flush_title(session, title_task):
              yield title_event
      finally:
          if title_task is not None and not title_task.done():
              title_task.cancel()
  ```

  ```python
  async def _emit_title_if_ready(self, session, title_task):
      if title_task is None or not title_task.done() or session.title.strip():
          return ()
      return await self._apply_title(session, title_task.result())

  async def _flush_title(self, session, title_task):
      if title_task is None or session.title.strip():
          return ()
      try:
          title = await title_task
      except asyncio.CancelledError:
          return ()
      return await self._apply_title(session, title)

  async def _apply_title(self, session, raw_title) -> tuple[SessionEvent, ...]:
      title = (raw_title.strip() or "New Session")[:120]
      session.title = title
      await self._persist_session(session=session)
      return (SessionTitleGenerated(title=title),)
  ```

  Notes:
  - `session.title = ...` uses the existing `Session.title` setter (`session.py:73`).
  - `session.title.strip()` becoming non-empty after `_apply_title` is the natural "already
    emitted" guard, so the title is emitted at most once.
  - All DB writes stay in this single coroutine — no concurrent `AsyncSession` use.
  - `finally` cancels a still-pending task if the agent run raises, avoiding orphaned tasks.
- Add `import asyncio` at the top.

### 4. Wire the new dependency — `infrastructure/di.py`

- `provide_session_management_service`: drop the `title_generator` argument and the
  `title_generator=` kwarg (matches step 1).
- `provide_session_conversation_service`: add `title_generator: SessionTitleGenerator`
  parameter and pass `title_generator=title_generator` into `SessionConversationService(...)`.

### 5. SSE event schema — `presentation/sse/events.py`

- Add enum member: `TITLE_GENERATED = "session.title_generated"` to `SessionEventType`.
- Add the event model:

  ```python
  class TitleGeneratedEvent(_SessionEventSchema):
      type: Literal[SessionEventType.TITLE_GENERATED] = SessionEventType.TITLE_GENERATED
      title: str
  ```

- Add `TitleGeneratedEvent` to the `ServerEvent` discriminated union (this is what drives the
  generated TS client, so it must be in the union).

### 6. SSE mapper — `presentation/sse/mappers.py`

- Import `SessionTitleGenerated` (from `application`) and `TitleGeneratedEvent`.
- Add a branch in `to_server_event`:

  ```python
  if isinstance(event, SessionTitleGenerated):
      return TitleGeneratedEvent(title=event.title)
  ```

No change needed in `sse/stream.py` (it just maps + serializes whatever events flow through).

### 7. Backend tests

- `SessionService.create` no longer calls the title generator and returns an empty-title
  session (update/replace existing create tests).
- `SessionConversationService.send_message`:
  - On a session with empty title, emits exactly one `SessionTitleGenerated` event with the
    generated (or `"New Session"` fallback) title and persists it.
  - On a session that already has a title, emits no title event and does not call the generator.
  - Title generator failure path: confirm the in-flight task is cancelled and the stream still
    completes (agent events unaffected). Consider catching generator exceptions inside
    `_flush_title`/`_emit_title_if_ready` and treating them as the `"New Session"` fallback so a
    title-LLM error never breaks the message stream — decide and test this explicitly.

---

## Frontend changes

### 8. Regenerate the API client

After the backend schema changes, run:

```
cd frontend
npm run generate:api
```

This regenerates `frontend/src/api/generated/**`. The new `TitleGeneratedEvent` flows into the
`SessionEventSchema.serverEvent` union, so `SessionServerEvent` in `api/session-stream.ts`
(derived from that union) automatically gains the `{ type: "session.title_generated"; title }`
variant — no manual edit to `session-stream.ts` needed.

### 9. Handle the event in the chat reducer — `pages/chat-page.state.ts`

In `reduceServerEvent`, add a case:

```ts
case "session.title_generated":
  return { ...state, title: event.title };
```

`state.title` is already surfaced by the hook (`title: state.title ?? session?.title`), so the
header updates reactively. The existing `invalidateSessionQueries()` at stream end refreshes the
sidebar list and the cached session so the title persists after the stream.

### 10. Expose a "title pending" flag — `pages/chat-page.hook.ts`

- Compute and return `isTitlePending`:

  ```ts
  const resolvedTitle = state.title ?? session?.title;
  const isTitlePending = !resolvedTitle?.trim();
  ```

  Return `title: resolvedTitle` and `isTitlePending` from the hook; add `isTitlePending` to
  `UseChatSessionResult`.

### 11. Title skeleton in the chat header — `pages/chat-page.tsx` + `components/chat/chat-page-header.tsx`

- `chat-page.tsx`: pull `isTitlePending` from `useChatSession` and pass it to `ChatPageHeader`.
  Stop forcing the `"Neues Karten-Deck"` fallback when a title is genuinely pending — pass the
  raw `title` through and let the header decide.
- `chat-page-header.tsx`: add an `isTitlePending?: boolean` prop. Render logic:
  - `isLoading` (session still loading) → existing `<Skeleton className="h-4 w-40" />`.
  - else if `isTitlePending` → render the same skeleton (title is generating). Keep the
    dropdown trigger usable for actions, or simply show the skeleton in place of the title text
    inside the trigger so rename/delete stay available.
  - else → real title as today.
  - Keep `"Neues Karten-Deck"` only as the fallback for the brand-new `/new` route where there
    is no session at all.

### 12. Sidebar skeleton for pending titles — `components/sidebar/sidebar-session-item.tsx`

A freshly created session is invalidated into the list immediately (empty title) and only gets
its real title after the first stream completes. Render a skeleton when the title is empty:

```tsx
{session.title.trim() ? (
  <span className="min-w-0 flex-1 truncate">{session.title}</span>
) : (
  <Skeleton className="h-3.5 w-32" />
)}
```

(Import the existing `Skeleton` from `@/components/ui/skeleton`. Also use a sensible
`aria-label` fallback for the actions dropdown trigger when `session.title` is empty.)

### 13. (Optional polish) home page

`home-page.tsx` needs no logic change — `createSession` is now fast because the title LLM call is
gone from the request path. Optionally tighten error copy, but functionally it already navigates
with `streamInitialResponse` + `initialPrompt`, which is exactly what now triggers both the
agent inference and (via the empty title) the async title generation.

---

## Edge cases & decisions

- **Title fallback**: preserve the original `(generated.strip() or "New Session")[:120]` so a
  blank LLM result still yields a stable, non-pending title (otherwise the skeleton would never
  resolve).
- **Generator error**: prefer falling back to `"New Session"` over surfacing an error on the
  message stream — a title failure must never block or break the chat. Implement in
  `_flush_title`/`_emit_title_if_ready`.
- **Already-titled sessions**: the empty-title guard ensures follow-up messages and existing
  sessions never regenerate or re-emit a title.
- **Stream stopped/cancelled early**: the `finally` block cancels the pending title task; the
  title simply stays pending and will be regenerated on the next message (still empty title).
- **Concurrency**: reaffirm — only the LLM HTTP call is concurrent; all `AsyncSession` access is
  serialized in the generator coroutine.

## Suggested implementation order

1. Backend events + conversation service + session service + DI (steps 1–4).
2. SSE schema + mapper (steps 5–6).
3. Backend tests (step 7); run the backend test suite.
4. `npm run generate:api` (step 8).
5. Frontend reducer + hook + header + sidebar (steps 9–12).
6. Manual verification: start a chat from the home page, confirm the first assistant tokens
   appear without waiting for the title, and the header/sidebar skeletons resolve to the real
   title mid-stream.
