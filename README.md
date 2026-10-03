## prompster

AI-powered Hitster playlist builder. Users describe a playlist in natural language; an agent researches Spotify, builds a draft, and can export a printable card deck as PDF.

### packages

| Package    | Role                                                                      |
| ---------- | ------------------------------------------------------------------------- |
| `callm`    | External chat model package for OpenAI and Codex providers               |
| `agent`    | Tool-calling agent loop, Spotify tools, workspace state, streaming events |
| `backend`  | FastAPI HTTP/WebSocket API, auth, sessions, PDF export, DB + S3                 |
| `frontend` | Lit SPA — chat UI, live RPC event rendering, Spotify deck player         |
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

For Docker, start the stack with the optional read-only Codex mount:

```bash
bash scripts/start_codex.sh
# Or run in the background:
bash scripts/start_codex.sh -d
```

The script works from any working directory, uses the repository's `.env`, checks
for a readable `auth.json`, and starts `docker compose up --build` with both
Compose files. Additional arguments are passed to `up`. Use Bash on Linux/macOS
or Git Bash on Windows; Docker Compose v2 is required.

Set `CODEX_AUTH_DIR` in `.env` to the absolute path of your logged-in Codex
directory (for example `C:/Users/you/.codex` on Windows or
`/home/you/.codex` on Linux). An exported `CODEX_AUTH_DIR` takes precedence. If
the value is empty or unset, the script uses `CODEX_HOME`, then `~/.codex`.

If your Codex login is stored in the OS credential store, create a file-based
login in the intended Codex home so the container can read `auth.json`:

```bash
codex -c 'cli_auth_credentials_store="file"' login
```

See the [Codex credential storage documentation](https://learn.chatgpt.com/docs/auth#credential-storage).
Select a **Codex** model in the UI to use this login. Backend features that use
the registry's default model still use OpenAI and require `OPENAI_API_KEY` with
the current configuration.

To manage the stack directly, set `CODEX_AUTH_DIR` explicitly and use both files:

```bash
docker compose -f compose.yml -f compose.codex.yml up --build
```

The login directory and `auth.json` must already exist. The default Compose
configuration only passes `OPENAI_API_KEY`; use the override to make Codex
subscription credentials available inside the backend container.

### workspace

This is a `uv` workspace. All packages share a single lockfile.

```bash
uv sync                 # install all packages
uv run backend          # start the API server
uv run agent            # run the agent standalone
```
