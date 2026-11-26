## backend package

FastAPI application that exposes the Prompster API, wires all features together via dependency injection, and bridges the frontend with the `agent` package.

Encapsulates:

- HTTP API under `/api/v1` with `dishka` DI container
- Google OAuth 2.0 authentication + JWT session management
- Persistent chat sessions with tool-call history (PostgreSQL via SQLModel / asyncpg)
- File storage for generated assets (S3 via obstore)
- Spotify integration (OAuth token management, playlist creation)
- PDF playlist deck generation (Typst + QR codes)
- Streaming agent runs over typed Canon server-sent events

### features

| Feature | Responsibility |
|---|---|
| `auth` | Google OAuth flow, JWT issuance & refresh, cookie handling |
| `session` | Chat session CRUD, agent run streaming, PDF export |
| `spotify` | Spotify account connection, playlist write-back |
| `user` | User profile read / update |

Each feature registers its routers and providers in `compose.py`.
The app assembles these registrations without making subpackage imports load the HTTP layer.

### architecture checks

Run the workspace policy from the repository root:

```bash
uvx --python 3.14 --from smelt-cli==0.18.0 smelt check --strict-coverage --fail-on warning
```

The commit hook checks staged changes and CI checks the full workspace.
The matching agent skill lives in [`.agents/skills/smelt`](../.agents/skills/smelt).

### session event streams

Agent runs and Spotify exports stream as server-sent events. Each stream is a
cookie-authenticated `POST` endpoint declared with `fastapi-canon`'s
`APIRouter.sse`:

| Endpoint | Body | Events |
|---|---|---|
| `POST /api/v1/sessions/{session_id}/messages` | `SendMessageRequest` | `SessionStreamEvent` |
| `POST /api/v1/sessions/{session_id}/onboarding/complete` | `CompleteOnboardingRequest` | `SessionStreamEvent` |
| `POST /api/v1/sessions/{session_id}/playlist/spotify-export` | none | `SpotifyExportEvent` |

Request validation and authentication run before the stream opens, so clients
get ordinary `422`/`401` problem responses. Every event is a `data:` frame;
Canon ends the stream with `canon.complete` or `canon.problem`. Each route opens
its application service through an APP-scoped `ServiceScope`, which keeps a
Dishka request scope alive for the stream's lifetime. Closing the HTTP
connection closes the application stream and cancels pending export tasks
before that scope is released. The integration uses `fastapi-canon[sse]`.

The stream code lives in `src/backend/features/session/presentation/streams/`:

- `router.py` declares the three SSE routes on `stream_router`.
- `events.py` defines the event payloads using `Schema` and camelCase wire names.
- `stream.py`, `mappers.py`, and `spotify_export.py` adapt application events and export progress.

Python modules use absolute imports. Relative imports are reserved for package
exports in `__init__.py`.

The OpenAPI contract in `schema/` and the TypeScript stream client are generated
from `codegen.toml`:

```bash
uv run --package backend fastapi-canon generate --config codegen.toml
uv run --package backend fastapi-canon generate --config codegen.toml --check
```

From `frontend/`, the equivalent commands are `npm run generate:streams` and
`npm run check:streams`. Commit the contract and the generated client in
`frontend/src/api/session-streams/` together; the CI check rejects stale
generated files. The frontend consumes each operation as a typed async iterable
over `fetch`, passing an `AbortSignal` to stop a stream and refreshing the
session cookie once on `401` before the stream starts.

### platform

- **Database** — async PostgreSQL via `asyncpg` + SQLModel ORM + Alembic migrations
- **Storage** — S3-compatible object storage via `obstore` (SeaweedFS locally)
- **DI** — `dishka` async container with per-request scoping

### running

```bash
uv run backend        # starts uvicorn on the configured port
```

Requires environment variables defined in settings modules (database URL, JWT secret, OAuth credentials, and S3 config).
