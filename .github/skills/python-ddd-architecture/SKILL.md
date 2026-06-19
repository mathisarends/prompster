---
name: python-ddd-architecture
description: >
  Folder structure, dependency rules, and conventions for building a Python (FastAPI + Dishka +
  SQLAlchemy) backend as self-contained feature slices. Use this when scaffolding a new project,
  adding a feature, adding a service/repository/router, or navigating the project structure.
  Apply it to reproduce this code philosophy consistently across any topic.
---

# Project Architecture

This is a **feature-sliced**, Domain-Driven backend. Each feature is a vertical slice with the same
four-layer structure and is fully self-contained. Features never import from each other's internals —
they are wired together only at the composition root.

Stack: **FastAPI** (HTTP), **Dishka** (dependency injection), **SQLAlchemy async** (persistence),
**Pydantic** (DTOs). Reproduce these conventions for any new feature or new project.

## Folder Structure

```
src/<package>/
├── main.py                       ← composition root (see below)
├── features/
│   └── <feature>/
│       ├── __init__.py           ← exposes ONE `feature = Feature(...)` object
│       ├── application/
│       │   ├── __init__.py       ← re-exports services + result types
│       │   ├── <feature>_service.py
│       │   └── exceptions.py
│       ├── domain/
│       │   ├── __init__.py       ← re-exports aggregates, ports, exceptions
│       │   ├── <aggregate>.py    ← subclasses Aggregate/Entity
│       │   ├── repository.py     ← abstract port (ABC) only
│       │   └── exceptions.py
│       ├── infrastructure/
│       │   ├── __init__.py       ← re-exports the Dishka provider
│       │   ├── di.py             ← Dishka Provider for this feature
│       │   └── repository.py     ← Sql* implementation of the port
│       └── presentation/
│           ├── __init__.py       ← re-exports router + register_*_exception_handlers
│           ├── router.py
│           ├── mapper.py         ← to_*_response functions (domain → DTO)
│           ├── schemas.py        ← Pydantic DTOs (subclass Schema)
│           └── exception_handlers.py
├── infrastructure/               ← cross-cutting providers (database, email, storage)
│   ├── database/
│   │   ├── orm.py                ← SQLAlchemy models (DatabaseEntity)
│   │   └── repository.py         ← generic Repository[ORM, Domain] base
│   └── di/
├── presentation/                 ← shared HTTP building blocks
│   ├── feature.py                ← the Feature dataclass
│   ├── schema.py                 ← Schema base (camelCase aliasing)
│   ├── errors.py                 ← ErrorDto
│   ├── pascal_case_router.py
│   └── health_router.py
└── shared/
    └── ddd.py                    ← Entity / Aggregate base classes
```

## The Feature Object & Composition Root

Every feature's top-level `__init__.py` exposes exactly one thing: a frozen `Feature` describing how
the slice plugs in. Nothing else about the feature is imported from outside.

```python
# features/<feature>/__init__.py
from <package>.presentation.feature import Feature

from .infrastructure.di import <Feature>Provider
from .presentation import register_<feature>_exception_handlers, <feature>_router

feature = Feature(
    name="<feature>",
    routers=[<feature>_router],
    providers=[<Feature>Provider],
    register_exception_handlers=register_<feature>_exception_handlers,
)

__all__ = ["feature"]
```

```python
# presentation/feature.py
@dataclass(frozen=True, slots=True)
class Feature:
    name: str
    routers: Sequence[APIRouter] = ()
    providers: Sequence[type[Provider]] = ()
    register_exception_handlers: Callable[[FastAPI], None] | None = None
```

`main.py` is the only place that knows the full feature list. It builds the app by iterating features:
mount routers under `/api/v1`, register exception handlers, and collect every feature provider plus the
shared infrastructure providers into one Dishka container. **Adding a feature = add its `feature` to the
`_FEATURES` list in `main.py` and nothing else.**

```python
_FEATURES = [auth.feature, payment.feature, user.feature, ...]
_INFRASTRUCTURE_PROVIDERS = [DatabaseProvider, EmailProvider, StorageBackendProvider]
```

## Dependency Rule

Dependencies point inward — never outward:

```
presentation → application → domain ← infrastructure
```

- `domain/` — pure Python, zero framework imports. Aggregates, ports (ABCs), domain exceptions, policies.
- `application/` — imports `domain/` only. No FastAPI, no SQLAlchemy. Orchestration lives here.
- `infrastructure/` — imports `domain/` to implement its ports; may import frameworks (SQLAlchemy, Dishka).
- `presentation/` — imports `application/` for services and `domain/` for the types it maps to DTOs.
  It must not import `infrastructure/`.

Features never import another feature's `application`/`infrastructure`/`presentation`. Importing another
feature's `domain` types (e.g. a shared `OAuthProvider` value) is the allowed seam; keep it minimal.

## Domain Layer

Aggregates subclass the shared `Aggregate` (alias of `Entity`), which supplies `id` and `created_at`.
Constructors are **keyword-only**, accept optional `id` / `created_time` (generated if absent), and hold
no framework types.

```python
# domain/<aggregate>.py
class User(Aggregate):
    def __init__(self, *, name: str, email: str, id: UUID | None = None,
                 created_time: datetime | None = None) -> None:
        super().__init__(id=id, created_time=created_time)
        self.name = name
        self.email = email
```

Repository **ports** are ABCs in `domain/repository.py` with keyword-only async methods. They name domain
types only — never ORM models.

```python
# domain/repository.py
class UserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, *, user_id: UUID) -> User | None: ...
    @abstractmethod
    async def create(self, *, user: User) -> User: ...
```

Domain exceptions are plain `Exception` subclasses that carry structured attributes (so the presentation
layer can map them to a response). Never raise HTTP exceptions in the domain or application layers.

```python
# domain/exceptions.py
class UserMessageQuotaExceededError(Exception):
    def __init__(self, *, limit: int, reset_at: datetime) -> None:
        super().__init__(f"Daily limit of {limit} reached.")
        self.limit = limit
        self.reset_at = reset_at
```

`domain/__init__.py` re-exports every public aggregate, port, policy, and exception with an explicit
`__all__`. Consumers import from the package, never from submodules.

## Application Layer — Service Pattern

Orchestration uses **service classes**, not one-handler-per-file command/query objects. A service groups
the related operations of a slice. Dependencies are injected via `__init__` and stored with a leading
underscore. Methods are async and take **keyword-only** arguments — no command/query DTOs.

```python
# application/<feature>_service.py
@dataclass(frozen=True)
class UserDeleteInformation:        # result type — return value, not input
    session_count: int

class UserService:
    def __init__(self, user_repository: UserRepository) -> None:
        self._user_repository = user_repository

    async def get_me(self, *, user_id: UUID) -> User:
        user = await self._user_repository.get_by_id(user_id=user_id)
        if user is None:
            raise SessionInvalidException("Invalid user")
        return user

    async def get_delete_information(self, *, user_id: UUID) -> UserDeleteInformation:
        ...
        return UserDeleteInformation(session_count=session_count)
```

- Inputs are keyword-only arguments — no input dataclasses.
- When a method returns multiple values, define a **frozen dataclass result type** (e.g.
  `UserDeleteInformation`, `UserMessageRateLimitSnapshot`).
- Services raise domain/application exceptions, never HTTP exceptions.
- Pure decision logic (e.g. rate-limit math) belongs in a `domain/*_policy.py` object the service consults.

`application/__init__.py` re-exports the services and their result types with an explicit `__all__`.

## Infrastructure Layer

### Repository implementation

Implementations are named `Sql<Aggregate>Repository`, subclass both the generic
`Repository[ORM, Domain]` base and the domain port, and translate via `_to_domain` / `_to_orm`. The
generic base supplies `find_by_id`, `find_by`, `save`, `delete_by_id`, `exists`, etc. ORM models never
leave this layer.

```python
# infrastructure/repository.py
class SqlUserRepository(Repository[UserModel, User], UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=UserModel)

    def _to_domain(self, orm: UserModel) -> User: ...
    def _to_orm(self, domain: User) -> UserModel: ...

    async def get_by_id(self, *, user_id: UUID) -> User | None:
        ...
```

### Dishka provider

Each feature has one `<Feature>Provider(Provider)` in `infrastructure/di.py` wiring ports → implementations
and constructing services. Choose the scope deliberately:

- `Scope.APP` — settings, stateless policies (built once).
- `Scope.REQUEST` — anything that touches the `AsyncSession`: repositories and services.

```python
class UserProvider(Provider):
    @provide(scope=Scope.APP)
    def provide_policy(self, settings: RateLimitSettings) -> UserMessageRateLimitPolicy: ...

    @provide(scope=Scope.REQUEST)
    def provide_user_service(self, user_repository: UserRepository) -> UserService:
        return UserService(user_repository=user_repository)
```

`infrastructure/__init__` (or `infrastructure/di/__init__`) re-exports the provider so the feature's
top-level `__init__` can import it.

## Presentation Layer

Routers use `DishkaRoute` and inject **services** (not repositories) via `FromDishka[<Service>]`. Each
route sets an explicit `operation_id`, `status_code`, `response_model`, and documents error responses with
`ErrorDto`. Call service methods with keyword arguments, then map the result to a DTO.

```python
# presentation/router.py
user_router = APIRouter(route_class=DishkaRoute, prefix="/users", tags=["users"])
_unauthorized = {status.HTTP_401_UNAUTHORIZED: {"model": ErrorDto}}

@user_router.get("/me", response_model=UserMeResponse, operation_id="get_me",
                 responses=_unauthorized)
async def get_me(
    authenticated_user_id: AuthenticatedUserId,
    service: FromDishka[UserService],
) -> UserMeResponse:
    user = await service.get_me(user_id=authenticated_user_id)
    return to_user_me_response(user=user)
```

Mapping domain → DTO lives in `mapper.py` as module-level `to_*_response` functions — keep it out of the
route body. Domain models must never be returned directly.

```python
# presentation/mapper.py
def to_user_me_response(user: User) -> UserMeResponse:
    return UserMeResponse(id=user.id, name=user.name, email=user.email)
```

DTOs subclass `Schema`, which applies camelCase aliasing and `from_attributes`:

```python
# presentation/schemas.py
class UserMeResponse(Schema):
    id: UUID
    name: str
    email: str
```

Domain exceptions are translated to HTTP responses in `exception_handlers.py`, exposed through a single
`register_<feature>_exception_handlers(app)` function — never inside a route or service.

```python
# presentation/exception_handlers.py
def register_user_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(UserMessageQuotaExceededError, _quota_exceeded_handler)
```

`presentation/__init__.py` re-exports the router and the `register_*_exception_handlers` function.

## Shared Building Blocks (reuse, don't reinvent)

- `shared/ddd.Entity` / `Aggregate` — id + created_at base for aggregates.
- `infrastructure/database/repository.Repository[ORM, Domain]` — generic CRUD base for repositories.
- `presentation/schema.Schema` — Pydantic base with camelCase aliasing; every DTO subclasses it.
- `presentation/errors.ErrorDto` — standard error body for `responses=`.
- `presentation/feature.Feature` — the slice descriptor consumed by `main.py`.

## Conventions Checklist

- Each layer exposes a single public surface via `__init__.py` with an explicit `__all__`; consumers
  import from the package, never from submodules.
- Use `X | None`, not `Optional[X]`. No mutable default arguments.
- Service/handler inputs are keyword-only arguments — no input/command/query dataclasses.
- Result types (multi-field return values) are **frozen dataclasses**.
- Generate IDs in the aggregate base (`uuid4()` default) — callers pass `id=None`.
- Repositories return domain objects, never ORM models; ORM stays inside `infrastructure/`.
- Routes inject services, set `operation_id`, and map through `mapper.py`.
- Domain/application raise domain exceptions; HTTP status mapping happens only in `exception_handlers.py`.

## Recipe: Add a New Feature

1. Create `features/<feature>/` with the four layers above.
2. `domain/`: aggregate(s) subclassing `Aggregate`, repository port ABC, exceptions, `__init__` re-exports.
3. `application/`: `<feature>_service.py` with a service class + any result dataclasses; `__init__` re-exports.
4. `infrastructure/`: `repository.py` (`Sql*` impl over `Repository[ORM, Domain]`) and `di.py`
   (`<Feature>Provider` binding port→impl and building the service); re-export the provider.
5. `presentation/`: `router.py`, `mapper.py`, `schemas.py`, `exception_handlers.py`; `__init__` re-exports
   `<feature>_router` and `register_<feature>_exception_handlers`.
6. Top-level `__init__.py`: build the `feature = Feature(...)` object.
7. Register the slice by adding `<feature>.feature` to `_FEATURES` in `main.py`.
