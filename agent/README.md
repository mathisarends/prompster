## agent package

Autonomous tool-calling agent for Spotify playlist research, shared across the workspace.

Encapsulates:

- Agentic run loop via `Agent` with configurable max iterations
- Streaming event model (`AgentEvent` subclasses)
- Tool registry with DI-injected dependencies (`Tools`, `ToolContext`)
- Spotify interaction via `spotifyify` (`Spotify`)
- Workspace state for playlist drafts (`PlaylistDraftStore`)

Both `backend` and standalone scripts depend on this package so agent logic and tool definitions live in one place.

### agent

```python
class Agent:
    def __init__(
        self,
        llm: ChatModel,
        tools: Tools | None = None,
        messages: MessageManager | None = None,
        max_iterations: int = 10,
        system_prompt: str | None = None,
        spotify: Spotify | None = None,
        playlist_store: PlaylistDraftStore | None = None,
    ) -> None: ...

    async def prepare(self) -> None          # opens Spotify session
    async def close(self) -> None            # closes Spotify session if owned
    async def stream(message: str) -> AsyncGenerator[AgentEvent, None]
    async def resume(tool_call_id: str, answer: str) -> AsyncGenerator[AgentEvent, None]
    def reset(self) -> None                  # clears message history
```

`stream` starts a new run; `resume` injects a follow-up answer and continues a suspended run.

### events

Each step of the run loop yields a typed event:

```python
RunStartedEvent(message: str)
StepStartedEvent(step: int)
ToolCallEvent(name: str, args: dict)
ToolResultEvent(name: str, result: str)
WorkspaceUpdatedEvent(playlist_draft: PlaylistDraft)
FollowUpRequestedEvent(tool_call_id: str, questions: list[AskFollowUpQuestion])
AssistantMessageEvent(content: str)
RunCompletedEvent(output: str)
```

When `FollowUpRequestedEvent` is yielded the run suspends — call `resume()` with the user's answer to continue.

### tools

Register tools with the `@tools.action(...)` decorator:

```python
tools = Tools()

@tools.action(
    description="Search Spotify for tracks matching a query.",
    status_label=lambda p: f"Searching '{p.query}'",
    params=SearchParams,
)
async def search_tracks(spotify: Inject[Spotify], params: SearchParams) -> str:
    return await spotify.search_tracks(params)
```

Default tools cover: `search_tracks`, `search_albums`, `search_playlists`, `get_artist_albums`, `get_artist_top_tracks`, `get_album_tracks`, `get_spotify_playlist_tracks`, `build_draft_playlist`, `ask_follow_up`.

Dependencies (`Spotify`, `PlaylistDraftStore`) are resolved at call time via `ToolContext`.
