# Agent Context Management – Implementation Plan

## Goal

Reduce token usage in long sessions while preserving full agent capability. The core idea: tool call/result pairs from **completed** turns are expensive and redundant once the workspace draft captures their outcome. Compress them away, but keep full fidelity for the **current** turn so multi-step tool chains still work.

---

## Architecture

### Message layout produced by `MessageManager.all()`

```
[SystemMessage]          ← static system prompt + dynamically injected <workspace_state>
[UserMessage]            ← compressed turn 1 (user text only)
[AssistantMessage]       ← compressed turn 1 (final assistant text only)
[UserMessage]            ← compressed turn 2
[AssistantMessage]       ← compressed turn 2
...
[UserMessage]            ← current turn (with optional <user_events> prepended)
[AssistantMessage]       ← current turn step 1 (with tool_calls)
[ToolResultMessage]      ← current turn tool result 1
[AssistantMessage]       ← current turn step 2 (with tool_calls)
[ToolResultMessage]      ← current turn tool result 2
...                      ← all steps of active turn preserved in full
```

**Key invariant:** previous turns → zero tool call/result tokens.  
**Workspace state** is always fresh in the system message → no information is lost.

---

## Changes

### 1. `messages.py` – `MessageManager` refactor

**New internal state:**
```python
@dataclass
class CompressedTurn:
    user: str
    assistant: str  # final assistant text (no tool calls)

class MessageManager:
    _compressed_history: list[CompressedTurn]  # replaces _messages
    _current_turn: list[Message]               # active turn, full fidelity
    _workspace: WorkspaceStore | None          # for fresh XML injection
```

**`all()` – dynamic build:**
```python
def all(self) -> list[Message]:
    system_content = self._system_prompt
    if self._workspace and (draft := self._workspace.playlist_draft):
        system_content += "\n\n" + self._render_workspace_xml(draft)
    
    msgs = [SystemMessage(content=system_content)]
    for turn in self._compressed_history:
        msgs.append(UserMessage(content=turn.user))
        msgs.append(AssistantMessage(content=turn.assistant, tool_calls=[]))
    msgs.extend(self._current_turn)
    return msgs
```

**`add_user()` – accepts optional user events:**
```python
def add_user(self, content: str, user_events: str | None = None) -> None:
    full = f"{user_events}\n\n{content}" if user_events else content
    self._current_turn.append(UserMessage(content=full))
```

**`compress_current_turn()` – called by Agent on RunCompleted:**
```python
def compress_current_turn(self) -> None:
    user_text = next(
        (m.content for m in self._current_turn if isinstance(m, UserMessage)), ""
    )
    final_assistant = ""
    for m in reversed(self._current_turn):
        if isinstance(m, AssistantMessage) and not m.tool_calls:
            final_assistant = m.content
            break
    if user_text or final_assistant:
        self._compressed_history.append(CompressedTurn(user_text, final_assistant))
    self._current_turn.clear()
```

**`_render_workspace_xml()` – workspace state as XML:**
```xml
<workspace_state>
  <draft name="80er Pop Mix" tracks="20">
    <track id="a1b2" uri="spotify:track:abc" title="Take On Me"
           artist="A-ha" year="1985" pinned="true"/>
    <!-- ... -->
  </draft>
</workspace_state>
```

**`reset()` – clears both layers:**
```python
def reset(self) -> None:
    self._compressed_history.clear()
    self._current_turn.clear()
```

**Constructor signature:**
```python
def __init__(
    self,
    system_prompt: str | None = None,
    workspace: WorkspaceStore | None = None,
) -> None:
```

---

### 2. `agent.py` – Agent wires it together

**Pass workspace to MessageManager:**
```python
self._messages = messages or MessageManager(
    system_prompt=system_prompt,
    workspace=self._workspace_store,
)
```

**Compress after RunCompleted:**
```python
# In _run_loop(), before yielding RunCompletedEvent:
self._messages.compress_current_turn()
yield RunCompletedEvent(output=completion)
return
```

**Pass user_events through stream():**
```python
async def stream(
    self, message: str, user_events: str | None = None
) -> AsyncGenerator[AgentEvent, None]:
    self._messages.add_user(message, user_events=user_events)
    yield RunStartedEvent(message=message)
    async for event in self.continue_stream():
        yield event
```

---

## Tradeoff

| | Before | After |
|---|---|---|
| Completed turns | All tool calls + results in full | Only (user text, final assistant text) |
| Current turn | Full fidelity | Full fidelity (unchanged) |
| Workspace knowledge | Implicit in tool results | Explicit XML in system message, fresh every call |
| Token cost per turn | Grows O(n) with all prior searches | Grows O(compressed_turns) only |
| Agent can re-read past searches | Yes (expensive) | No – but draft state replaces that need |

The agent never needs to re-read a past `search_tracks` result because:
1. Every track it added is in the draft
2. The draft is injected fresh in the system message every call
3. Any manual user changes become visible through `<user_events>` (future: sourced from session events)

---

## Future: user_events injection

The caller (session router) can pass a formatted `user_events` string to `agent.stream()` describing manual workspace changes since the last turn. The `WorkspaceStore` can expose a separate `drain_user_events()` or the session layer assembles them from frontend events.
