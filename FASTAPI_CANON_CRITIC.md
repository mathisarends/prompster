# fastapi-canon integration notes

This file records concrete feedback discovered while integrating `fastapi-canon`
into Prompster's backend. It intentionally focuses on observed integration
friction rather than hypothetical API preferences.

## Review status

Prompster was migrated to `fastapi-canon` 0.2.0 on 2026-09-10. The release
addresses the issues found during the 0.1.0 integration. Backend tests pass,
application composition succeeds, and the compiled OpenAPI correctly separates
JSON, empty, SSE, PDF, domain-error, and validation responses. Two API ergonomics
and OpenAPI edge cases remain below.

## Resolved in 0.2.0

### Composition-level router options

`Composition.router_factory` now supplies the shared `/api/v1` prefix and the
application's `PascalCaseRouter`. Feature declarations contribute their original
routers directly, so the previous wrapper-router-per-feature adapter is gone.

Prompster intentionally mounts `/health` and `/readiness` before applying the
composition because these process-level probes remain outside the versioned API.
This is an application boundary choice rather than missing composition support.

### Feature identity for diagnostics

Features now have required, unique names. Prompster names every bounded-context
and infrastructure feature, and 0.2.0 uses those names in composition diagnostics.

### Lazy provider construction

Provider classes and zero-argument factories are accepted and materialized once
during `Composition.apply()`. Prompster now contributes provider classes without
eagerly instantiating them in static feature declarations.

### Explicit container ownership

The installed documentation now states that `Composition` builds, exposes, and
closes the shared Dishka container, composes existing application lifespans, and
that applications must not close the container independently. This resolves the
migration ambiguity noted for 0.1.0.

### Generic normalized HTTP contracts

`ErrorRegistry.responses(http_statuses=[...])` now provides reusable OpenAPI
contracts for normalized `HTTPException` statuses. Prompster currently uses
domain exceptions for its presentation checks, so no route needs this argument
today, but the missing capability is present.

### Manual non-canon responses

Manual FastAPI response declarations without `x-fastapi-canon-errors` are now
accepted. The readiness route's non-problem JSON 503 response therefore no longer
needs the empty-extension workaround.

### Success media contracts

The immutable `Response` contract and its constructors cover the concrete
integration cases that previously required handwritten response dictionaries:

- `Response.empty()` documents all 204 routes without generated content.
- `Response.sse()` documents session event streams as only `text/event-stream`.
- `Response.binary("application/pdf")` documents the playlist export and its
  `Content-Disposition` header.
- `Response.json()` gives the health and readiness probes exact success schemas.
- `Response.empty(status=307)` removes spurious JSON content from redirect
  responses and documents their `Location` header.

OpenAPI compilation removes FastAPI's generated success media type in each of
these cases while retaining `application/problem+json` for declared failures.

### Public error data and broad exception types

The 0.2.0 documentation explicitly identifies `detail`, extensions, and headers
as public response data, recommends specific domain exception types, and warns
that broad built-ins such as `Exception`, `ValueError`, and `RuntimeError` can
hide programming failures. This addresses both earlier safety concerns.

### Streaming boundary

The documentation now explains that failures after response headers are sent
cannot become Problem Details, recommends completing preflight checks before
returning a stream, and distinguishes typed SSE failure events from incomplete
binary downloads. This matches Prompster's session-stream design.

## Remaining feedback

### Success-only routes still require an ErrorRegistry

`Response` contracts can only be attached through
`ErrorRegistry.responses(success=...)`. A route with no domain errors must
therefore call an unrelated registry or create an empty one. Prompster's health
router currently declares `_SYSTEM_RESPONSES = ErrorRegistry(errors=(),
name="system")` solely to use `Response.json()`.

A public response compiler such as `Response.responses()`, or accepting a
`Response` directly through a small route helper, would make success-only and
process-level endpoints feel independent of the error subsystem while preserving
the same canon metadata and OpenAPI compilation behavior.

### Empty non-204 contracts do not independently suppress generated JSON

`Response.empty(status=307)` does not remove FastAPI's generated
`application/json` response when the route decorator leaves its response class at
the default. The success marker uses `None` to mean no media type, and that marker
is absent from the intermediate OpenAPI document by the time canon compiles it.

Prompster's redirect routes therefore also set
`response_class=RedirectResponse`. That produces the intended content-free 307
contract, but the extra setting should not be necessary for the documented rule
that a declared `Response` replaces FastAPI's generated success media type. A
non-null internal sentinel for the no-content case, or applying the success tuple
collected from route contracts directly, would make `Response.empty(status=...)`
self-sufficient for all supported 2xx and 3xx statuses.
