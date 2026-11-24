## agent package

Prompster's deck-building agent. It is a thin layer over [harnessed](https://github.com/mathisarends/harnessed): one live harnessed session, a set of plugins, and nothing that harnessed already does.

```
agent/
├── agent.py          Agent: opens the session, streams turns, pause/resume/stop/abort
├── events.py         AgentEvent: the union of stream events the agent yields
├── instructions.md   shared system prompt; plugins add their own sections
├── activity/         UI labels for tool calls (call envelopes) → ToolCallAnnouncedEvent
├── conversation/     user input, checkpoints, provider replay, finished replies
├── research/         Spotify search tools → TracksFoundEvent, PlaylistsFoundEvent, SpotifyRetryEvent
├── deck/             deck tools and live deck state → Deck*Event
├── onboarding/       clarifying questions → QuestionAskedEvent
└── review/           deck balance critique
```

Each capability package holds its plugin, tools and events. Tools follow harnessed's idiom: flat signatures with `Annotated[..., Field(...)]` parameters and the docstring as description; short plugin instructions live inline next to the plugin. Only standalone prompts (`instructions.md`, the compaction and critic prompts) are Markdown files.

### agent

```python
async with Agent(
    llm,                       # pydantic_ai model
    phase=Phase.BUILD,
    deck=deck,                 # the workspace deck, or None
    checkpoint=checkpoint,     # AgentCheckpoint from the last commit, or None
    on_commit=save,            # async (AgentCommit) -> None
    session_id=str(session.id),
) as agent:
    async for event in agent.stream(text, images=images, curation_events=events):
        ...
```

`pause()`, `resume()`, `stop()` and `abort()` act on the running turn from any task, so an HTTP request can pause a turn that a websocket is streaming. Status changes arrive on the stream as `SessionStatusChangedEvent`.

### events

Plugins emit typed events through harnessed (`ctx.emit` in tools, `SessionContext.emit` in hooks). They reach `session.stream` like harnessed's own events, and `Agent.stream` yields the subset in `AgentEvent`:

| Event | From |
| --- | --- |
| `TextDeltaEvent`, `AssistantRepliedEvent` | harnessed, `ReplyPlugin` |
| `ToolCallAnnouncedEvent`, `ToolCallFinishedEvent` | `ToolActivityPlugin`, harnessed |
| `TracksFoundEvent`, `PlaylistsFoundEvent`, `SpotifyRetryEvent` | `ResearchPlugin` |
| `DeckCreatedEvent`, `DeckTracksAdded/Removed/ReplacedEvent` | `DeckPlugin` |
| `QuestionAskedEvent` | `OnboardingPlugin` |
| `CompactionStarted/Applied/FinishedEvent` | harnessed compaction |
| `SessionStatusChangedEvent`, `TurnResultEvent` | harnessed run control |

Plugins also listen to each other's events: `DeckPlugin` remembers the tracks in every `TracksFoundEvent`, so their URIs stay addable.

### persistence

Each `AgentCommit` holds harnessed's `SessionExecution` and, when history changed, its `SessionState`, both as JSON. Store them (two JSONB columns) and pass them back as `AgentCheckpoint` to reopen the agent where it stopped. Plugin state such as the deck's track catalog is saved with it as a harnessed `SessionValue`. A checkpoint saved while paused reopens idle, ready for the next message.

### context management

- The current deck is appended to each request as `<deck_state>` and is never stored in the history, so the cached prompt prefix stays valid.
- harnessed compacts the history at 80% of the context window and after a provider context-length error, keeping the last three steps.
- `ProviderReplayGuard` drops provider replay state from replies of another model, so a conversation can switch models.
