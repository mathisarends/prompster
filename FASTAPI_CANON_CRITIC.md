# fastapi-canon integration notes

This file records concrete feedback discovered while integrating `fastapi-canon`
into Prompster's backend. It intentionally focuses on observed integration friction
rather than hypothetical API preferences.

## Feature composition

### Missing composition-level router options

Prompster mounts all feature routers below `/api/v1` and applies a custom
`APIRouter` subclass for response serialization. `Composition` can only flatten
and install the routers contributed by each `Feature`; it cannot apply a shared
prefix, tags, dependencies, or router class to them.

The integration therefore needs a small application-side adapter that creates one
wrapper router per feature and includes the feature's actual routers in it. A
composition-level `router`/`router_factory` option, or mount options on `Feature`,
would make this common versioned-API setup considerably more direct.

In this project the wrapper is a `PascalCaseRouter`. Its only customization sets
`response_model_by_alias=True`, which is already FastAPI's default. That makes the
class effectively redundant today, but the integration still has to preserve it
until the project deliberately removes that abstraction. More generally,
`Composition` should make it possible to retain a shared application router class
without introducing one wrapper router for every feature.

### No feature identity for diagnostics

The library's `Feature` deliberately has no `name`. This keeps the declaration
small, but validation errors can consequently only describe conflicting
contributions, not the feature that contributed them. Named features would make
composition failures easier to locate in a backend with several bounded contexts.

### Provider classes versus instances

Prompster previously declared Dishka provider classes and instantiated them while
building the application container. `fastapi-canon.Feature` accepts only provider
instances. This is workable, but it makes otherwise static feature declarations
perform eager construction and differs from Dishka's common `make_container(P())`
composition style. Accepting provider factories/classes, or documenting why eager
instances are required, would improve the ergonomics.

### Lifespan/container ownership is implicit

`Composition` correctly owns and closes the Dishka container it creates, which is
useful. That ownership is not obvious at the call site, however, and an existing
application lifespan can easily close `app.state.dishka_container` a second time.
Clearer documentation around lifecycle ownership would help migrations from a
manual Dishka setup.

## Error handling

### Global exception normalization is a strong default

The consistent RFC 9457 response shape for domain errors, validation errors,
`HTTPException`, response-validation failures, and unhandled exceptions is a clear
improvement over Prompster's former collection of hand-written JSON handlers.
Using one `Error` definition for both runtime rendering and OpenAPI also removes a
real source of drift.

### Generic HTTP errors are difficult to declare per route

Authentication dependencies and a few presentation checks intentionally raise
FastAPI/Starlette `HTTPException` with different status codes. The runtime handler
normalizes these well, but `ErrorRegistry.responses()` is centered on domain
exception definitions and offers no equivalent reusable contract for a generic
401/403/404 HTTP problem. Applications must retain manual response declarations,
invent domain exceptions for presentation concerns, or leave those responses less
precisely documented.

### Manual response definitions are incorrectly rejected

Version 0.1.0 rejects every manual FastAPI `responses={...}` entry that does not
contain `x-fastapi-canon-errors`. In `contracts._errors_from_responses`, the
missing extension defaults to a tuple, immediately followed by validation that
requires a list. This affects unrelated success/media contracts such as SSE, PDF,
and a readiness response.

The absence of the extension should mean "this response declares no canon
errors". Prompster currently has to add `"x-fastapi-canon-errors": []` to each
manual response as a workaround. This is the most concrete integration bug found
so far.

### Broad base exceptions expose a useful safety check, but migration is subtle

Prompster previously mapped every `ValueError` to HTTP 400. Registering such a
broad built-in exception in an error registry is technically possible, but it can
hide programming defects as client errors. The library could explicitly warn in
documentation against registering broad built-in types such as `Exception`,
`ValueError`, or `RuntimeError` as domain contracts.

### Exception-string detail renderers are an easy data-leak footgun

The `detail` callback is useful, but the most obvious migration helper is
effectively `lambda exception: str(exception)`. That can unintentionally expose
internal identifiers, provider messages, or later implementation details. The
library should prominently recommend stable `code` values as the client contract
and advise that dynamic details must be explicitly classified as safe before they
are rendered. A secure example that does not echo exception strings would set a
better default.

### Streaming errors need a separate contract story

Exceptions raised while an async response body is being streamed occur after the
HTTP response has started. They cannot be converted into Problem Details by an
exception handler. Prompster's session stream therefore reports those failures as
typed SSE events, while only pre-stream failures can use `ErrorRegistry`.

This is an HTTP limitation rather than a handler bug, but the route-contract API
makes it easy to document a domain `Error` as an HTTP response even when it can
only occur inside a stream. Guidance or an explicit streaming/preflight example
would prevent misleading OpenAPI contracts.
