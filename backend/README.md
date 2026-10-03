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
Dishka request scope for its entire lifetime. Unsubscribe and disconnect close
the application stream and cancel pending export tasks before releasing that
scope. The integration uses `pyrpckit[codegen,dishka,fastapi]==0.10.0`.

Session subscriptions yield `SessionStreamEvent`; Spotify exports yield
`SpotifyExportEvent`. Clients initiate these streams with RPC calls and typed
parameters. The API does not define client event payloads.

The RPC code lives in `src/backend/features/session/presentation/rpc/`:

- `__init__.py` exports `rpc_router` and `contract` for application wiring and codegen.
- `channel.py` declares the typed methods and subscriptions with `Inject`.
- `context.py` holds the authenticated session identity; it is never a public parameter.
- `params.py` and `events.py` define RPC payloads using `RpcModel` and camelCase wire names.
- `stream.py`, `mappers.py`, and `spotify_export.py` adapt application events and export progress.
- `contract.py` declares the service and socket, then derives its OpenRPC contract.
- `router.py` mounts that socket through `RpcRoutes` and the Dishka adapter.

Python modules use absolute imports. Relative imports are reserved for package
exports in `__init__.py`.

The OpenRPC contract and TypeScript client are generated from `rpcgen.toml`:

```bash
uv run --package backend rpckit generate --config rpcgen.toml
uv run --package backend rpckit generate --config rpcgen.toml --check
```

From `frontend/`, the equivalent commands are `npm run generate:rpc` and
`npm run check:rpc`. Commit the contract in `schema/session-stream.openrpc.json`
and the generated client in `frontend/src/api/session-rpc/` together; the CI
check rejects stale generated files. The frontend calls `client.session` methods
and consumes their typed async iterables. Its shared connection helper derives
the socket path from the generated endpoint, supports `AbortSignal` during the
handshake and streaming, and closes the client after each operation.

### platform

- **Database** — async PostgreSQL via `asyncpg` + SQLModel ORM + Alembic migrations
- **Storage** — S3-compatible object storage via `aioboto3`
- **DI** — `dishka` async container with per-request scoping

### running

```bash
uv run backend        # starts uvicorn on the configured port
```

Requires environment variables defined in settings modules (database URL, JWT secret, OAuth credentials, and S3 config).
