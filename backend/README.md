## backend package

FastAPI application that exposes the Prompster API, wires all features together via dependency injection, and bridges the frontend with the `agent` package.

Encapsulates:

- HTTP & SSE API under `/api/v1` with `dishka` DI container
- Google OAuth 2.0 authentication + JWT session management
- Persistent chat sessions with tool-call history (PostgreSQL via SQLModel / asyncpg)
- File storage for generated assets (S3 via aioboto3)
- Spotify integration (OAuth token management, playlist creation)
- PDF playlist deck generation (Typst + QR codes)
- Streaming agent runs over SSE

### features

| Feature | Responsibility |
|---|---|
| `auth` | Google OAuth flow, JWT issuance & refresh, cookie handling |
| `session` | Chat session CRUD, agent run streaming, PDF export |
| `spotify` | Spotify account connection, playlist write-back |
| `user` | User profile read / update |

### session SSE stream

Agent events emitted by the `agent` package are mapped to server-sent events and streamed to the client:

```
POST /api/v1/sessions/{id}/run   → starts or resumes an agent run
GET  /api/v1/sessions/{id}/run   → SSE stream of AgentEvent → ServerEvent
GET  /api/v1/sessions/{id}/export → streams a PDF deck
```

### platform

- **Database** — async PostgreSQL via `asyncpg` + SQLModel ORM + Alembic migrations
- **Storage** — S3-compatible object storage via `aioboto3`
- **DI** — `dishka` async container with per-request scoping

### running

```bash
uv run backend        # starts uvicorn on the configured port
```

Requires environment variables defined in settings modules (database URL, JWT secret, OAuth credentials, and S3 config).
