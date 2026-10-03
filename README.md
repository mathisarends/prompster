## prompster

AI-powered Hitster playlist builder. Users describe a playlist in natural language; an agent researches Spotify, builds a draft, and can export a printable card deck as PDF.

### packages

| Package    | Role                                                                      |
| ---------- | ------------------------------------------------------------------------- |
| `callm`    | External chat model package for OpenAI and Codex providers               |
| `agent`    | Tool-calling agent loop, Spotify tools, workspace state, streaming events |
| `backend`  | FastAPI HTTP/WebSocket API, auth, sessions, PDF export, DB + S3                 |
| `frontend` | React SPA — chat UI, live RPC event rendering, Spotify deck player        |
| `tokens`   | Standalone token utilities                                                |

### how the pieces fit together

```
frontend  ──JSON-RPC──►  backend  ──────►  agent  ──►  callm
                       │                │
                  PostgreSQL        Spotify API
                  S3 / PDF
```

1. **frontend** sends a user message to `backend` and opens a JSON-RPC subscription.
2. **backend** creates or resumes a `Session`, delegates to the `agent` package, and maps each `AgentEvent` to a typed RPC event.
3. **agent** runs a tool-calling loop: it calls Spotify APIs and builds a `PlaylistDraft` in the `PlaylistDraftStore`.
4. **callm** provides the `ChatModel` used by both `agent` (tool calls) and `backend` (simple session chat). The backend model registry selects OpenAI API key or Codex subscription authentication.
5. Once the draft is finalised the user can export a PDF deck or write the playlist back to their Spotify account — both handled by `backend`.

The model selector identifies each provider explicitly:

- **OpenAI** models use `callm.ChatOpenAIResponses` and `OPENAI_API_KEY` from `.env`.
- **Codex** models use `callm.ChatCodex` with your ChatGPT subscription login from `codex login`. They do not use `OPENAI_API_KEY`.

For a local backend, log in with `codex login` before selecting a Codex model.
`callm` reads the login from `~/.codex/auth.json`, or from `CODEX_HOME` when set.

For Docker, set `CODEX_AUTH_DIR` in `.env` to the absolute path of your logged-in
Codex directory (for example `C:/Users/you/.codex` on Windows or
`/home/you/.codex` on Linux), then enable the optional read-only mount:

```bash
docker compose -f compose.yml -f compose.codex.yml up --build
```

The login directory must already exist. The default Compose configuration only
passes `OPENAI_API_KEY`; use the override to make Codex subscription credentials
available inside the backend container.

### workspace

This is a `uv` workspace. All packages share a single lockfile.

```bash
uv sync                 # install all packages
uv run backend          # start the API server
uv run agent            # run the agent standalone
```
