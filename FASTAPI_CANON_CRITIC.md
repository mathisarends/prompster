# fastapi-canon integration notes

This file records concrete feedback discovered while integrating `fastapi-canon`
into Prompster's backend. It intentionally focuses on observed integration
friction rather than hypothetical API preferences.

## Review status

Prompster was migrated to `fastapi-canon` 0.3.0 on 2026-09-10. All route
modules now use `CanonRouter`, success contracts use the first-class `response=`
argument, and error contracts use composable `raises=` declarations. The full
backend suite passes, and the generated OpenAPI retains the expected JSON,
empty, redirect, SSE, PDF, domain-error, and validation contracts.

No outstanding library defect was found during this migration. The two concrete
issues remaining after the 0.2.0 integration are resolved in 0.3.0.

## Resolved in 0.3.0

### Canonical route declarations

`CanonRouter` removes the need to manually combine
`ErrorRegistry.responses(...)` dictionaries in every decorator. Prompster now
attaches each feature's registry once through `errors=`, declares authentication
once at router level, and adds operation-specific failures through `raises=`.

The shared `PascalCaseRouter` now subclasses `CanonRouter`, preserving the
application-wide `/api/v1` composition prefix and response alias behavior while
making the composition router canon-aware.

### First-class success contracts

Success contracts are declared directly through `response=`:

- `CanonResponse.empty()` describes 204 operations.
- `CanonResponse.empty(status=307)` describes redirects and their `Location`
  header.
- `CanonResponse.sse()` describes session streams as `text/event-stream`.
- `CanonResponse.binary("application/pdf")` describes the playlist PDF and its
  `Content-Disposition` header.
- `CanonResponse.json()` gives the health and readiness probes exact schemas.

The contract status now supplies FastAPI's route status, so duplicate
`status_code=` declarations were removed where a `CanonResponse` is present.

### Success-only routes no longer need an error registry

`CanonResponse.responses()` and `CanonRouter(response=...)` make success
contracts independent of the error subsystem. Prompster's health router no
longer creates an empty `ErrorRegistry` merely to compile health and readiness
responses.

### Bodyless non-204 responses

`CanonResponse.empty(status=307)` now suppresses FastAPI's generated JSON
content by itself. Prompster's Google and Spotify redirect routes no longer need
`response_class=RedirectResponse` as an OpenAPI workaround. Their handlers
still return `RedirectResponse` instances at runtime.

### Clear response naming and early declaration checks

The rename from `Response` to `CanonResponse` removes the import alias required
beside FastAPI and Starlette response classes. `CanonRouter` also rejects
conflicting status declarations, manual response collisions, and an explicit
body-producing `response_model` combined with a bodyless response contract.

### Public OpenAPI compilation hook

Contract compilation now operates on the generated OpenAPI document through the
documented `app.openapi` hook instead of copying or traversing FastAPI's internal
route tree during composition. Prompster calls `app.openapi()` immediately after
all routers are registered, so application-level registry and normalization
errors fail during application construction even when documentation endpoints
are disabled in production.

## Retained 0.2.0 improvements

The 0.2.0 composition features remain in use: named features, lazy Dishka
provider construction, composition-level `router_factory`, explicit container
ownership, normalized HTTP exception contracts, safe public Problem Details
guidance, manual non-canon response support, and documented streaming failure
boundaries. Health and readiness remain intentionally unversioned because they
are process-level probes rather than feature API routes.

## Operational caveats

Application-level contract validation occurs when `app.openapi()` is generated.
Applications that disable documentation and never build the schema should add an
explicit startup or test-time call if they want these checks to fail fast.

Routes with `include_in_schema=False` are intentionally outside document-level
validation, and router-level `raises=` applies only to operations declared on
that router, not to separately included child routers. Both behaviors are
documented; Prompster's hidden OAuth callbacks have no canon declarations, and
each included feature router owns its own registry and shared errors.
