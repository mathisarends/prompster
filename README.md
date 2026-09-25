## prompster

AI-powered Hitster playlist builder. Users describe a playlist in natural language; an agent researches Spotify, builds a draft, and can export a printable card deck as PDF.

### packages

| Package    | Role                                                                      |
| ---------- | ------------------------------------------------------------------------- |
| `llm`      | Thin factory for OpenAI `ChatModel` instances, shared credential loading  |
| `agent`    | Tool-calling agent loop, Spotify tools, workspace state, streaming events |
| `backend`  | FastAPI HTTP/WebSocket API, auth, sessions, PDF export, DB + S3                 |
| `frontend` | React SPA — chat UI, live RPC event rendering, Spotify deck player        |
| `tokens`   | Standalone token utilities                                                |

### how the pieces fit together

```
frontend  ──JSON-RPC──►  backend  ──────►  agent  ──►  llm
                       │                │
                  PostgreSQL        Spotify API
                  S3 / PDF
```

1. **frontend** sends a user message to `backend` and opens a JSON-RPC subscription.
2. **backend** creates or resumes a `Session`, delegates to the `agent` package, and maps each `AgentEvent` to a typed RPC event.
3. **agent** runs a tool-calling loop: it calls Spotify APIs and builds a `PlaylistDraft` in the `PlaylistDraftStore`.
4. **llm** provides the `ChatModel` used by both `agent` (tool calls) and `backend` (simple session chat).
5. Once the draft is finalised the user can export a PDF deck or write the playlist back to their Spotify account — both handled by `backend`.

### workspace

This is a `uv` workspace. All packages share a single lockfile.

```bash
uv sync                 # install all packages
uv run backend          # start the API server
uv run agent            # run the agent standalone
```
