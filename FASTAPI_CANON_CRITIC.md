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

The two concrete issues remaining after the 0.2.0 integration are resolved for
Prompster's composed application. One success-only integration edge case and a
few smaller DX opportunities remain below.

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
contracts independent of a router-local error registry. Prompster's health
router no longer creates an empty `ErrorRegistry` merely to declare health and
readiness responses. The application-level limitation described under remaining
feedback still applies.

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

## Remaining feedback from Prompster's DX

### A success-only application still needs the registry OpenAPI hook

A standalone `CanonRouter` with only `response=CanonResponse.json(...)` or
`CanonResponse.empty(status=307)` does not install the OpenAPI compiler. Without
an `ErrorRegistry.install(...)` elsewhere in the application, generated OpenAPI
still exposes `x-fastapi-canon-success`; a bodyless 307 also retains FastAPI's
generated `application/json` content.

Prompster's unversioned health router works because the feature composition
installs a domain error registry for the rest of the application. It is therefore
router-local success-only, but not application-level success-only. This coupling
is easy to miss when extracting probes into a small app or test fixture.

A public success-contract OpenAPI installer, automatic hook installation by
composition even when no error registry exists, or success declarations that do
not require a later cleanup hook would make the advertised success-only path
self-contained.

### Registry ownership is declared twice

The same feature registry is passed to `CanonRouter(errors=...)` so `raises=` can
be validated and to `Feature(errors=...)` so composition can install it. In
Prompster this duplication appears for auth, session, OAuth connections, and
Spotify. The user router also consumes the auth registry while the auth feature
owns its application-level contribution, which makes the distinction between
"used by this router" and "installed by this feature" important but implicit.

Allowing a feature to collect registries from its canon routers, or offering a
single feature-router declaration that establishes both relationships, would
reduce wiring while retaining explicit ownership for shared registries.

### Shared contracts repeat across sibling routers

The session feature has three sibling routers with the same `SESSION_ERRORS`
registry and authentication requirement. Because router-level `raises=` does not
flow into included child routers, each sibling repeats `errors=SESSION_ERRORS`
and `raises=(AUTHENTICATION_REQUIRED_ERROR,)`.

An explicit router-group context or opt-in inheritance during `include_router`
would improve larger feature modules without making the existing non-inheritance
rule ambiguous.

### OpenAPI validation has no intention-revealing entry point

Prompster calls `app.openapi()` during app construction solely to run the
application-level canon checks. A public `Composition.validate(app)` or
`validate_openapi_contracts(app)` API would express that intent more clearly and
could avoid making callers depend on schema generation and caching as the
validation mechanism.
