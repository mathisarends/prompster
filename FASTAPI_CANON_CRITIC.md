# fastapi-canon integration notes

This file records concrete feedback discovered while integrating `fastapi-canon`
into Prompster's backend. It intentionally focuses on observed integration
friction rather than hypothetical API preferences.

## Review status

Prompster was migrated to `fastapi-canon` 0.4.0 on 2026-09-10. All route
modules use `CanonRouter`, success contracts use the first-class `response=`
argument, and error contracts use composable `raises=` declarations. The
application validates its contracts explicitly during construction.

Version 0.4.0 resolves three concrete DX issues recorded during the 0.3.0
integration: success-only OpenAPI compilation, duplicate registry ownership,
and the lack of an intention-revealing validation entry point. One repeated
sibling-router declaration remains as feedback below.

## Resolved in 0.4.0

### Registry and raised-error terminology

Prompster's canon routers now receive their available error catalog through
`error_registry=`. Router-level and operation-level `raises=` continue to state
which errors an operation may actually produce. The names make that distinction
clear at the declaration site.

### Registry ownership is inferred from routers

Feature declarations no longer repeat `errors=` after their routers already
declare `error_registry=`. `Feature` collects those direct router contributions,
and composition merges identical registries.

This also handles Prompster's shared auth registry naturally: both the auth and
user routers contribute `AUTH_ERRORS`, while composition installs the identical
registry only once. The local `api_feature()` helper consequently no longer
accepts or forwards an error registry.

### Explicit contract validation

Prompster now calls `_COMPOSITION.validate(app)` after applying composition.
This expresses the fail-fast intent directly instead of calling `app.openapi()`
for its validation side effect. Contract errors are therefore still detected
during application construction when documentation endpoints are disabled in
production.

### Self-contained success contracts

Composition installs the OpenAPI compiler even when no error registry exists,
and low-level applications can use `install_openapi_contracts(app)` explicitly.
A standalone success-only `CanonRouter` no longer leaks
`x-fastapi-canon-success` metadata or retains FastAPI's generated JSON content
for a bodyless response.

Prompster's unversioned health router therefore no longer depends indirectly on
an unrelated domain error registry for correct OpenAPI output.

## Current integration

Success contracts remain declared directly through `response=`:

- `CanonResponse.empty()` describes 204 operations.
- `CanonResponse.empty(status=307)` describes redirects and their `Location`
  header.
- `CanonResponse.sse()` describes session streams as `text/event-stream`.
- `CanonResponse.binary("application/pdf")` describes the playlist PDF and its
  `Content-Disposition` header.
- `CanonResponse.json()` gives the health and readiness probes exact schemas.

The contract status supplies FastAPI's route status, so these routes do not
duplicate `status_code=`. Redirect handlers still return `RedirectResponse` at
runtime, and streaming handlers still return `StreamingResponse`; neither needs
a response-class declaration solely to repair OpenAPI.

The shared `PascalCaseRouter` subclasses `CanonRouter`, preserving the
application-wide `/api/v1` composition prefix and response alias behavior while
making the composition router canon-aware.

Named features, lazy Dishka provider construction, the composition-level
`router_factory`, normalized HTTP exception contracts, and safe public Problem
Details handling remain in use. Health and readiness stay intentionally
unversioned because they are process-level probes rather than feature routes.

## Operational caveats

Routes with `include_in_schema=False` are intentionally outside document-level
validation. Router-level `raises=` applies only to operations declared directly
on that router, not to separately included child routers. Prompster's hidden
OAuth callbacks have no canon declarations, and each included feature router
owns its own registry and shared errors.

## Remaining feedback from Prompster's DX

### Shared contracts repeat across sibling routers

The session feature has three sibling routers with the same `SESSION_ERRORS`
registry and authentication requirement. Because router-level declarations do
not flow into separately contributed sibling routers, each repeats
`error_registry=SESSION_ERRORS` and
`raises=(AUTHENTICATION_REQUIRED_ERROR,)`.

An explicit router-group context or opt-in inheritance during `include_router`
could reduce this repetition for larger feature modules while keeping the
existing non-inheritance rule predictable.
