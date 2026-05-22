# Time to First Token Improvement

## Problem

Heute dauert das Erstellen einer Session unnötig lang:

1. `POST /sessions` ruft **synchron** `LLMSessionTitleGenerator.generate()` auf (`session_service.py:32`).
   Das ist ein eigener LLM-Call, bevor wir die Session überhaupt persistieren oder zurückgeben.
2. Erst wenn dieser Call durch ist, antwortet die Route mit `SessionResponse`.
3. Das Frontend (`home-page.tsx:27`) wartet auf diese Response, navigiert dann nach
   `/chat/{id}` und startet **erst dort** das eigentliche Streaming des Agenten via
   `POST /sessions/{id}/messages` (`chat-page.hook.ts:200`).

Der User sieht also: Spinner auf Home → Navigation → Spinner auf Chat → erste Tokens.
Die wahrgenommene Latenz bis zum ersten Token ist `Title-LLM-Call + Navigation + Stream-Start`.

## Ziel (Claude-like UX)

- User drückt "Senden" → ist sofort auf der Chat-Page mit der eigenen Nachricht sichtbar.
- Tokens des Agenten streamen sofort (keine LLM-Roundtrip-Wartezeit für etwas anderes).
- Der Titel taucht **danach** dynamisch auf — über denselben SSE-Stream.

## Lösungsidee (Architektur)

Ein einziger kombinierter SSE-Endpoint `POST /sessions/stream`, der

1. die Session **ohne** Title-Wait anlegt (Title bekommt einen Platzhalter),
2. sofort ein `session.created`-Event sendet, damit das Frontend die URL aktualisieren kann,
3. parallel zwei Tasks startet:
   - **Task A**: `SessionConversationService._run_agent(...)` — produziert die Assistant-/Tool-/Follow-Up-Events.
   - **Task B**: `SessionTitleGenerator.generate(initial_prompt)` — produziert ein einziges `session.title_updated`-Event.
4. Beide Tasks in eine `asyncio.Queue` mergen und gemeinsam über den Stream rausgeben.

Damit ist die `time-to-first-token` praktisch nur noch `DB-Insert + LLM-TTFT`. Der Title-Call
läuft parallel und blockiert nichts.

Der alte synchrone `POST /sessions` wird **vollständig entfernt** — keine Legacy-
Koexistenz. Ein einziger Pfad zum Anlegen einer Session, sowohl im Backend als auch
im Frontend.

---

## Backend-Implementierung

### B1. Title nicht mehr blockierend in `SessionService.create`

**Datei**: `backend/src/backend/features/session/application/session_service.py`

- `create()` setzt einen **Platzhalter-Titel** aus dem `initial_prompt` (z.B. erste ~60
  Zeichen, getrimmt, ohne Punctuation am Ende). Kein LLM-Call mehr in diesem Pfad.
- `SessionTitleGenerator` wird aus dem Konstruktor von `SessionService` entfernt
  (oder bleibt drin und wird nur noch von einer neuen `generate_title`-Methode benutzt —
  siehe unten).
- Neue Methode `regenerate_title(*, session_id, user_id) -> str` für späteres
  manuelles Triggern (optional; nice to have, aber nicht Teil dieses Tickets).

**Helfer für Platzhalter** (privat in der Datei):
```python
def _placeholder_title_from_prompt(initial_prompt: str) -> str:
    cleaned = " ".join(initial_prompt.split())
    truncated = cleaned[:60].rstrip(" .,!?;:-—")
    return truncated or "Neues Karten-Deck"
```

### B2. Neue Application-Service-Methode für den kombinierten Flow

**Datei**: `backend/src/backend/features/session/application/conversation_service.py`
(oder neue `session_bootstrap_service.py` — siehe Hinweis am Ende)

Neue Methode auf `SessionConversationService`:

```python
async def create_and_stream(
    self,
    *,
    owner_id: UUID,
    initial_prompt: str,
) -> AsyncIterator[SessionEvent]:
    ...
```

Verantwortlichkeiten:

1. Session via `SessionService.create(...)` (mit Platzhalter-Titel) anlegen + persistieren.
2. Sofort `SessionCreated(session=session)` yielden (siehe B3).
3. **Parallel** starten:
   - `title_task = asyncio.create_task(self._generate_title_event(session.id, initial_prompt))`
   - `agent_iter = self._run_agent(session=session)`
4. Beide Streams via `asyncio.Queue` mergen und yielden (siehe Merge-Pattern unten).
5. Wenn `title_task` fertig ist:
   - Title in DB updaten (`session_repository.update(session_id, title=...)`).
   - `SessionTitleUpdated(session_id, title)` durch die Queue schicken.
6. Wenn `title_task` failed: still ignorieren / loggen — Platzhalter-Titel bleibt stehen.

**Merge-Pattern** (vereinfacht):

```python
async def _merge_streams(
    self,
    agent_events: AsyncIterator[SessionEvent],
    background_tasks: list[asyncio.Task[SessionEvent | None]],
) -> AsyncIterator[SessionEvent]:
    queue: asyncio.Queue[SessionEvent | _Sentinel] = asyncio.Queue()

    async def pump_agent() -> None:
        try:
            async for event in agent_events:
                await queue.put(event)
        finally:
            await queue.put(_AGENT_DONE)

    async def pump_task(task: asyncio.Task[SessionEvent | None]) -> None:
        try:
            event = await task
            if event is not None:
                await queue.put(event)
        except Exception:
            logger.exception("background task failed")

    agent_pump = asyncio.create_task(pump_agent())
    task_pumps = [asyncio.create_task(pump_task(t)) for t in background_tasks]

    agent_done = False
    pending_tasks = len(task_pumps)
    while not agent_done or pending_tasks > 0:
        item = await queue.get()
        if item is _AGENT_DONE:
            agent_done = True
            continue
        yield item
        # decrement pending_tasks when a background task's pump finishes — track via Done sentinels
```

(Anmerkung: Implementierung muss sauber alle Cancel-/Cleanup-Pfade abdecken. Bei
`asyncio.CancelledError` im äußeren Generator müssen `agent_pump`, alle `task_pumps`
und `agent_events.aclose()` gecancelt werden, sonst leaken wir DB-Connections/Tasks.)

### B3. Neue Domain-Events

**Datei**: `backend/src/backend/features/session/application/events.py`

```python
@dataclass(frozen=True)
class SessionCreated:
    session: Session

@dataclass(frozen=True)
class SessionTitleUpdated:
    session_id: UUID
    title: str
```

Beide ins `SessionEvent` Union aufnehmen.

### B4. Presentation-Layer SSE-Events

**Datei**: `backend/src/backend/features/session/presentation/sse/events.py`

```python
class SessionEventType(StrEnum):
    SESSION_CREATED = "session.created"            # NEU
    SESSION_TITLE_UPDATED = "session.title_updated" # NEU
    # ... bestehende Werte
```

```python
class SessionCreatedEvent(_SessionEventSchema):
    type: Literal[SessionEventType.SESSION_CREATED] = SessionEventType.SESSION_CREATED
    session: SessionSnapshotPayload

class SessionTitleUpdatedEvent(_SessionEventSchema):
    type: Literal[SessionEventType.SESSION_TITLE_UPDATED] = (
        SessionEventType.SESSION_TITLE_UPDATED
    )
    session_id: UUID
    title: str
```

Beides ins `ServerEvent`-Union aufnehmen.

**Datei**: `backend/src/backend/features/session/presentation/sse/mappers.py`

`to_server_event(...)` muss `SessionCreated` und `SessionTitleUpdated` mappen können.
(Vor allem `SessionCreated` braucht das gleiche Snapshot-Mapping wie der existierende
`session.snapshot` Pfad — am besten Mapping-Helper rausziehen.)

### B5. Route ersetzen (volle Migration)

**Datei**: `backend/src/backend/features/session/presentation/router.py`

Die bestehende `create_session`-Route (`router.py:125`) wird **ersetzt** durch eine
SSE-Variante mit demselben Pfad `POST /sessions`:

```python
@router.post(
    "",
    status_code=status.HTTP_200_OK,
    operation_id="create_session",
    responses=_event_stream_response | _auth_errors | _bad_request,
)
async def create_session(
    authenticated_user_id: AuthenticatedUserId,
    body: SessionCreateRequest,
    service: FromDishka[SessionConversationService],
) -> StreamingResponse:
    return stream_session_events(
        service.create_and_stream(
            owner_id=authenticated_user_id,
            initial_prompt=body.initial_prompt,
        )
    )
```

- Status-Code wechselt von `201 CREATED` auf `200 OK` (SSE-Konvention, konsistent mit
  den anderen Stream-Routen `/messages`, `/follow-ups`).
- `SessionResponse` als `response_model` entfällt — `SessionResponse` wird stattdessen
  in den `SessionCreatedEvent` als Snapshot eingebettet.
- Kein `/stream`-Suffix nötig — es gibt nur noch diesen einen Weg.

Außerdem in `SessionService`:

- `create()` als public Method **entfällt** — sie wird nur noch intern von
  `SessionConversationService.create_and_stream` benutzt. Entweder
  - in `SessionConversationService` als private Helper-Methode inlinen, oder
  - `SessionService.create()` als private/internal Method behalten und aus dem
    public Interface (Mapper / Frontend-Codegen) rausnehmen.

  **Empfehlung**: Helper-Methode in `SessionConversationService`, weil die Title-
  Generation jetzt ohnehin im Conversation-Flow lebt — keine Notwendigkeit, das
  über zwei Services zu spannen.

### B6. DI Update

**Datei**: `backend/src/backend/features/session/infrastructure/di.py`

`SessionConversationService` braucht zusätzlich `SessionTitleGenerator`. Da `create()`
aus `SessionService` rauswandert, fällt der `title_generator`-Param dort weg —
`provide_session_management_service` wird entsprechend schlanker:

```python
@provide(scope=Scope.REQUEST)
def provide_session_management_service(
    self,
    session_repository: SessionRepository,
    session_summary_query: SessionSummaryQuery,
) -> SessionService:
    return SessionService(
        session_repository=session_repository,
        session_summary_query=session_summary_query,
    )

@provide(scope=Scope.REQUEST)
def provide_session_conversation_service(
    self,
    session_repository: SessionRepository,
    runner: SessionRunner,
    title_generator: SessionTitleGenerator,
) -> SessionConversationService:
    return SessionConversationService(
        session_repository=session_repository,
        runner=runner,
        title_generator=title_generator,
    )
```

### B7. Tests

- Unit: `SessionService.create` setzt Platzhalter-Titel, ruft den TitleGenerator
  **nicht** auf.
- Unit: `SessionConversationService.create_and_stream` emittiert in dieser Reihenfolge:
  `session.created` → mind. ein `message.assistant_*` Event → irgendwann
  `session.title_updated` → `done`.
- Unit: Wenn TitleGenerator wirft → kein Crash, kein Title-Event, Stream endet sauber
  mit `done`.
- Unit: Wenn Client den Stream abbricht (CancelledError) → keine offenen Tasks, kein
  DB-Lock.
- Integration: kompletter Roundtrip durch HTTP-Client, parsing der SSE-Events.

### B8. OpenAPI Spec

Nach den Schema-Änderungen muss der Client-Codegen-Build neu laufen, damit das Frontend
die neuen Event-Typen kennt (`session.created`, `session.title_updated`). Skript:
siehe `frontend/orval.config.ts` o.ä. (Befehl im Repo prüfen).

---

## Frontend-Implementierung

### F1. Neuer Stream-Helper

**Datei**: `frontend/src/api/session-stream.ts`

Neue Funktion:

```ts
type StreamCreateSessionOptions = StreamSendMessageOptions & {
  onSessionCreated?: (sessionId: string, snapshot: SessionSnapshotPayload) => void;
  onTitleUpdated?: (sessionId: string, title: string) => void;
};

export const streamCreateSession = async (
  body: SessionCreateRequest,
  options: StreamCreateSessionOptions,
) => streamSessionRequest("/api/v1/sessions/stream", body, options);
```

Im internen `handleEvent`-Switch zwei neue Cases:

```ts
case "session.created":
  options.onSessionCreated?.(event.session.id, event.session);
  break;
case "session.title_updated":
  options.onTitleUpdated?.(event.sessionId, event.title);
  break;
```

### F2. HomePage: kein blockierendes `createSession()` mehr

**Datei**: `frontend/src/pages/home-page.tsx`

Neuer Flow in `startChat`:

1. **Sofort** zu einer "Pending"-Chat-Page navigieren. Zwei Optionen:
   - (a) Eigene Route `/chat/new` mit `state: { pendingPrompt: text }`.
   - (b) Stay-and-stream auf der HomePage — verwerfen, weil Layout-Wechsel zu Claude-Feel gehört.

   **Empfehlung: (a)** mit einem Sentinel-Routing-Element, das eine Variante von
   `ChatPage` rendert, die noch keine `sessionId` hat.

2. Den Stream **nicht** auf der HomePage starten — sondern erst nach Navigation auf der
   ChatPage. Grund: Wenn der Stream auf der HomePage startet und der User direkt
   wegnavigiert, würde der Stream gecancelt. Stattdessen: `pendingPrompt` per
   `location.state` mitgeben, ChatPage übernimmt den Stream-Aufruf.

3. `queryClient.invalidateQueries(getListSessionsQueryKey())` wird **später** in der
   ChatPage getriggert (sobald `session.created` reinkommt), nicht mehr hier.

### F3. ChatPage / `chat-page.hook.ts`: Pending-Mode

**Datei**: `frontend/src/pages/chat-page.hook.ts` + `chat-page.tsx`

Neue Eingangs-Parameter:

```ts
type UseChatSessionParams = {
  sessionId?: string;              // optional, kann initial undefined sein
  initialSession?: SessionResponse;
  streamInitialResponse?: boolean; // legacy, irgendwann entfernen
  pendingPrompt?: string;          // NEU
};
```

**Verhalten im Pending-Mode (`!sessionId && pendingPrompt`)**:

1. Skip `useGetSession`-Query (`enabled: false`).
2. Optimistisch eine User-Nachricht ins State stecken
   (`dispatch({ type: "stream/started", userMessageText: pendingPrompt })`).
3. `streamCreateSession(...)` aufrufen mit:
   - `onSessionCreated(id, snapshot)`:
     - URL via `navigate(\`/chat/\${id}\`, { replace: true, state: { session: snapshot } })`
       updaten. **replace: true** ist wichtig — kein zusätzlicher History-Eintrag.
     - `dispatch({ type: "session/loaded", session: snapshot })` — übernimmt
       die echten Entry-IDs (z.B. die echte User-Message-ID statt der optimistischen).
     - `queryClient.invalidateQueries(getListSessionsQueryKey())` — Sidebar updaten.
   - `onTitleUpdated(id, title)`:
     - `dispatch({ type: "session/title_updated", title })` (neuer Action-Typ).
     - `queryClient.setQueryData(getGetSessionQueryKey(id), (old) => old ? { ...old, title } : old)`.
     - Sidebar via `invalidateQueries` refreshen.
   - `onEvent`: bestehender Pfad (alle anderen Events).
4. AbortController-Cleanup wie bei den anderen Streams.

### F4. Reducer: neue Actions

**Datei**: `frontend/src/pages/chat-page.state.ts`

```ts
export type ChatAction =
  | // ... bestehende
  | { type: "session/title_updated"; title: string };
```

```ts
case "session/title_updated":
  return { ...state, title: action.title };
```

### F5. Header: Titel-Loading-State

**Datei**: `frontend/src/components/chat/chat-page-header.tsx` (lesen + ggf. anpassen)

Wenn `title` noch ein Platzhalter ist (oder per Flag `isTitlePending` markiert):

- Entweder Platzhalter-Titel ("Neues Karten-Deck" oder den abgeschnittenen Prompt)
  anzeigen, oder
- Ein dezent animiertes Skeleton-Element (wie Claude: kurz leer / shimmering, dann
  erscheint der Titel).

Empfehlung: Platzhalter-Titel direkt anzeigen, beim `session.title_updated`-Event
weich austauschen (kein Layout-Shift). Optional `transition-opacity` für den
Cross-Fade.

### F6. Sidebar-Liste

Die `getListSessionsQueryKey()` Query liefert Sessions inkl. Title. Solange der Title
noch nicht generiert ist, zeigt die Sidebar den Platzhalter. Nach dem
`session.title_updated`-Event triggern wir `invalidateQueries`, dann holt React Query
den aktualisierten Title. Kein zusätzlicher State nötig.

### F7. Tests

- Component/Integration: HomePage submit → navigiert auf `/chat/new` ohne auf API zu
  warten.
- Mock-Stream: `session.created`-Event → URL ändert sich auf `/chat/{id}`, History-
  Eintrag wird ersetzt (kein Browser-Back zur HomePage über `/chat/new`).
- Mock-Stream: `session.title_updated`-Event → Header zeigt neuen Titel, Sidebar
  refresht.
- Abort-Verhalten: User klickt während Stream weg → AbortController feuert, keine
  Errors im Console.

---

## Rollout & Open Questions

- **Breaking Change (bewusst)**: Es gibt nur noch **einen** Weg, eine Session anzulegen
  — den SSE-Endpoint. Der alte sync `POST /sessions` mit JSON-Response wird entfernt.
  Da das Frontend der einzige Consumer ist, ist die Migration atomar:
  Backend-Änderung + Frontend-Änderung + Codegen müssen in derselben PR landen.
  `streamInitialResponse`-Flag in `chat-page.hook.ts` (legacy, siehe `chat-page.hook.ts:54`)
  fällt komplett weg, ebenso der `state.session`-Pfad in `home-page.tsx:31`.
- **`streamSendMessage` für die erste Message entfällt für den Initial-Flow**: Da der
  Agent direkt im `create_session`-SSE läuft, wird die initiale Assistant-Antwort
  **nicht** mehr separat über `POST /sessions/{id}/messages` gestreamt. Der bestehende
  Pfad bleibt für alle Folgenachrichten unverändert.
- **Bootstrap-Service vs. Conversation-Service**: `create_and_stream` könnte auch in
  einen eigenen `SessionBootstrapService` ausgelagert werden, um Coupling zwischen
  Title-Generation und Conversation klein zu halten. Würde aber zusätzliche DI-Logik
  bedeuten. **Entscheidung**: erstmal in `SessionConversationService` lassen; refaktorn
  falls die Methode zu fett wird.
- **Pending-Prompt Persistenz**: Was passiert, wenn der User mitten im Stream den Tab
  reloaded? Aktuell: Verlust des Pending-Prompts. Akzeptabel, weil die User-Message
  schon auf dem Server persistiert wurde (Schritt 1 von `create_and_stream`), d.h.
  nach Reload bekommt der User die Session inklusive seiner Nachricht zu sehen — nur
  ohne weiteres Streaming. Optional später: Resume-Endpoint, der ab dem letzten
  persistierten Assistant-Chunk weiterstreamt.
- **Title nachträglich regenerieren**: Wenn der Title-Generator failed, gibt es im
  ersten Wurf keinen Retry. Nice-to-have: Cron oder manueller Button. Out of scope.
