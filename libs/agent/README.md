## agent package

Prompster's deck-building agent, built on [harnessed](https://github.com/mathisarends/harnessed) and shared across the workspace.

Encapsulates:

- One harnessed session per run, wrapped by `Agent`
- A stable streaming event model (`AgentEvent` subclasses)
- Tools and prompts per capability, as harnessed plugins
- Spotify interaction via `spotifyify` (`Spotify`)
- Workspace state for Hitster deck drafts (`DeckStore`)

### agent

```python
class Agent:
    def __init__(
        self,
        llm: pydantic_ai.models.Model,
        history: Sequence[harnessed.models.Message] | None = None,
        system_prompt: str | None = None,
        spotify: Spotify | None = None,
        deck_store: DeckStore | None = None,
        max_deck_tracks: int = 50,
        phase: Phase = Phase.ONBOARDING,
        max_input_tokens: int | None = None,
        compaction_threshold: float = 0.8,
    ) -> None: ...

    async def close(self) -> None            # closes the Spotify session
    def request_stop(self) -> None           # aborts the running session
    async def stream(message=None, curation_events=None) -> AsyncGenerator[AgentEvent, None]
```

Without a `message`, the trailing user message in `history` starts the run.

### plugins

| Plugin | Phase | Responsibility |
| --- | --- | --- |
| `OnboardingPlugin` | onboarding | Asks questions and suspends the run for the answer |
| `ResearchPlugin` | build | Read-only Spotify tools that run in parallel |
| `DeckPlugin` | build | Deck edits, plus the live deck state on every request |
| `ReviewPlugin` | build | Static balance checks, with an LLM critique only when they find a concern |
| `EventBridge` | both | Translates harnessed events into `AgentEvent`s and runs the final guardrails |

UI labels (`status`, `sequence_label`) are call envelopes. harnessed removes them before a tool runs, and a missing or invalid label never fails a call.

### context management

- Prompts live in `messages/prompts/`, one file per capability, and form a stable system prefix.
- The current deck is appended to each request as `<deck_state>` and is never stored in the history, so the cached prompt prefix stays valid.
- Track results from earlier runs are replayed as stable digests without their expired URIs.
- harnessed compacts the history at 80% of the context window and after a provider context-length error.

### events

Each step of the run yields a typed event:

```python
RunStartedEvent(message: str)
StepStartedEvent(step: int)
ToolCallEvent(name: str, args: dict)
ToolResultEvent(name: str, result: str)
DeckUpdatedEvent(deck_draft: DeckDraft)
AssistantMessageEvent(content: str)
RunCompletedEvent(output: str)
```
