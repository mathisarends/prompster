## backend package

FastAPI application that exposes the Prompster API, wires all features together via dependency injection, and bridges the frontend with the `agent` package.

Encapsulates:

- HTTP & WebSocket API under `/api/v1` with `dishka` DI container
- Google OAuth 2.0 authentication + JWT session management
- Persistent chat sessions with tool-call history (PostgreSQL via SQLModel / asyncpg)
- File storage for generated assets (S3 via aioboto3)
- Spotify integration (OAuth token management, playlist creation)
- PDF playlist deck generation (Typst + QR codes)
- Streaming agent runs over rpckit subscriptions

### features

| Feature | Responsibility |
|---|---|
| `auth` | Google OAuth flow, JWT issuance & refresh, cookie handling |
| `session` | Chat session CRUD, agent run streaming, PDF export |
| `spotify` | Spotify account connection, playlist write-back |
| `user` | User profile read / update |

### session RPC stream

`/api/v1/sessions/{session_id}/stream` is a cookie-authenticated WebSocket
endpoint. The presentation layer exposes `send_message`, `complete_onboarding`,
and `export_spotify` as typed rpckit subscriptions. Each subscription uses a
Dishka request scope; application services and domain events remain unchanged.

The OpenRPC contract and TypeScript client are generated from `rpcgen.toml`:

```bash
uv run --package backend rpckit generate --config rpcgen.toml
uv run --package backend rpckit generate --config rpcgen.toml --check
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
