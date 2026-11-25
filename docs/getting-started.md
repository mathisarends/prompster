# Local setup

[Back to the README](../README.md)

The default setup runs the backend, PostgreSQL, and SeaweedFS (S3-compatible object storage) in Docker. Vite runs separately on the host. Commands below are run from the repository root; on Windows, use Git Bash for the Bash scripts and `cp` examples, or `Copy-Item .env.example .env` in PowerShell.

## Configure the environment

Copy `.env.example` to `.env`. Replace the placeholder values for services you use, and leave optional Google credentials empty if you only use Spotify sign-in.

| Variable | Value for local development |
| --- | --- |
| `SPOTIFY_CLIENT_ID` | Client ID from your Spotify developer app |
| `SPOTIFY_CLIENT_SECRET` | Client secret from the same app |
| `SPOTIFY_REDIRECT_URI` | `http://127.0.0.1:8000/api/v1/auth/spotify/callback` |
| `SPOTIFY_TOKEN_ENCRYPTION_KEY` | A Fernet key, generated below |
| `OPENAI_API_KEY` | Your API key; required by the default OpenAI model configuration |
| `GOOGLE_CLIENT_ID` | Optional Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Optional Google OAuth client secret |
| `GOOGLE_REDIRECT_URI` | `http://127.0.0.1:8000/api/v1/auth/google/callback` when using Google |

Register the exact callback URI in each provider's app configuration. The frontend and callbacks must use the same hostname: use `127.0.0.1` throughout this setup.

Generate the Spotify token encryption key using the backend image:

```bash
docker compose build backend
docker compose run --rm --no-deps backend python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the output into `SPOTIFY_TOKEN_ENCRYPTION_KEY`. Keep this key stable so stored Spotify tokens remain decryptable.

If you already have the Python workspace installed, the equivalent command is:

```bash
uv run --package backend python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

The Compose file supplies local database, storage, and JWT defaults. `POSTGRES_*` and `S3_ACCESS_KEY`/`S3_SECRET_KEY` values in `.env` set the database and object-storage credentials; the S3 pair also signs in to the SeaweedFS admin UI. SeaweedFS creates the `STORAGE_BUCKET_NAME` bucket on startup. These defaults are intended for local development.

## Start the app

```bash
docker compose up --build -d
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend run dev
```

Compose creates the storage bucket and runs migrations before starting the API. Open [http://127.0.0.1:5173](http://127.0.0.1:5173).

Vite proxies HTTP and WebSocket requests under `/api` to `http://127.0.0.1:8000`. OAuth popups use the backend origin on port 8000. For separate origins, set `VITE_API_BASE_URL` and `VITE_OAUTH_BASE_URL` in `frontend/.env.local`; see [`frontend/.env.example`](../frontend/.env.example). Set `FRONTEND_BASE_URL` for the backend too if you change the frontend origin, and update your OAuth callbacks to match.

To inspect startup problems or stop the stack:

```bash
docker compose ps -a
docker compose logs --tail=100 backend migrate
docker compose down
```

`docker compose down` keeps the named database and storage volumes.

## Codex authentication

The model selector identifies each provider explicitly:

- **OpenAI** models use pydantic_ai's `OpenAIResponsesModel` and `OPENAI_API_KEY` from `.env`.
- **Codex** models use pydantic_ai's `OpenAICodexModel` with your ChatGPT subscription login from `codex login`. They do not use `OPENAI_API_KEY`.

For a local backend, log in with `codex login` before selecting a Codex model.
pydantic_ai reads the login from `~/.codex/auth.json`, or from `CODEX_HOME` when set, and never writes to it.

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

Model definitions and defaults live in [`backend/src/backend/features/llm/models.yml`](../backend/src/backend/features/llm/models.yml).

## Common issues

| Symptom | Check |
| --- | --- |
| Sign-in returns to the landing page | Frontend hostname, callback hostname, and registered redirect URI must agree. |
| Spotify settings fail validation | Replace all `SPOTIFY_*` placeholders and generate a valid Fernet key. |
| Agent requests fail with missing credentials | Check the selected model's provider and its credentials. Default background tasks use OpenAI. |
| Codex works locally but not in Docker | Use `scripts/start_codex.sh`; confirm the selected directory contains a readable `auth.json`. |
| Spotify playback is unavailable | In-browser playback requires a connected Spotify Premium account. |
| Backend does not start after a schema change | Inspect the `migrate` service logs and follow the [migration guide](migration.md). |

For the package boundaries, development checks, and code-generation commands, return to the [README](../README.md#development).
