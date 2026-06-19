---
name: python-ddd-architecture
description: >
  Folder structure, dependency rules, and conventions for adding features to this project.
  Use this when asked to add a feature, create a new domain, add a command, query, or handler,
  or when navigating the project structure.
---

# Project Architecture

This project follows **Domain-Driven Design** with a strict layered architecture per domain. Each domain is a vertical slice and fully self-contained.

## Folder Structure

```
src/
└── <domain>/
    ├── application/
    │   ├── __init__.py          ← re-exports everything public
    │   ├── commands/
    │   │   ├── __init__.py
    │   │   └── create_user.py   ← one file per command
    │   ├── queries/
    │   │   ├── __init__.py
    │   │   └── get_user.py      ← one file per query
    │   └── exceptions.py
    ├── domain/
    │   ├── __init__.py
    │   ├── aggregate.py
    │   ├── exceptions.py
    │   ├── ports.py             ← abstract repository interfaces only
    │   └── value_objects.py
    ├── infrastructure/
    │   ├── di/
    │   │   └── provider.py     ← Dishka provider for this domain
    │   ├── persistence/
    │   │   └── repository.py    ← implements ports.py
    │   └── adapters/            ← external services (email, S3, etc.)
    └── presentation/
        ├── router.py
        ├── schemas.py           ← Pydantic request/response DTOs
        └── exception_handlers.py
```

## Dependency Rule

Dependencies only point inward — never outward:

```
presentation → application → domain ← infrastructure
```

- `domain/` has zero framework imports — pure Python only
- `application/` imports from `domain/` only — no FastAPI, no SQLAlchemy
- `infrastructure/` imports from `domain/` to implement its ports
- `presentation/` imports from `application/` only — never from `domain/` or `infrastructure/` directly

Domains never import from each other. Cross-domain communication goes via domain events or a shared kernel.

## Commands & Queries

No command or query dataclasses. Handlers accept all inputs as keyword-only arguments directly on `handle()`:

```python
# application/commands/create_user.py
class CreateUserHandler:
    def __init__(self, user_repository: UserRepository) -> None:
        self._user_repository = user_repository

    async def handle(self, *, name: str, email: str, password: str) -> User:
        # ...
        return user
```

```python
# application/queries/get_projects.py
class GetProjectsHandler:
    def __init__(self, project_repository: ProjectRepository) -> None:
        self._project_repository = project_repository

    async def handle(self, *, user_id: UUID) -> list[Project]:
        # ...
        return projects
```

Result types (e.g. `CreateProjectResult`) are still dataclasses — they are return values, not inputs.

## Command & Query Handlers

Plain classes. Dependencies injected via `__init__`, stored with a leading underscore. The only public method is `handle`, which takes keyword-only arguments — no command or query objects.

Raise domain-specific exceptions — never HTTP exceptions inside handlers.

Every `application/` package exposes a single public surface via its `__init__.py`. Consumers import only from the package, never from submodules directly:

```python
# application/__init__.py
from .commands.create_user import CreateUserHandler
from .commands.delete_user import DeleteUserHandler
from .queries.get_user import GetUserHandler
from .exceptions import UserNotFoundException

__all__ = [
    "CreateUserHandler",
    "DeleteUserHandler",
    "GetUserHandler",
    "UserNotFoundException",
]
```

Consumers then import like:

```python
from domains.user.application import CreateUserHandler
```

The same pattern applies to `domain/` and `infrastructure/di/` — each layer exposes only what the next layer needs.

## Presentation Layer

Use `DishkaRoute` for dependency injection. Inject handlers via `FromDishka[HandlerType]`. Call `handle()` with keyword arguments directly — no command objects. Map domain objects to response schemas in a private `_to_*_response` helper at the bottom of the file — never let domain models leak into the response directly:

```python
from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter

router = APIRouter(route_class=DishkaRoute, prefix="/users", tags=["users"])

@router.post("/")
async def create_user(
    body: CreateUserRequest,
    handler: FromDishka[CreateUserHandler],
) -> UserResponse:
    user = await handler.handle(name=body.name, email=body.email, password=body.password)
    return _to_user_response(user)

def _to_user_response(user: User) -> UserResponse:
    return UserResponse(id=user.id, name=user.name, email=user.email)
```

Domain exceptions are mapped to HTTP responses in `exception_handlers.py` — never inside the handler or the route function.

## Re-exports via `__init__.py`

- Use `X | None` instead of `Optional[X]`
- One handler per file
- No command or query dataclasses — use keyword-only arguments on `handle()` instead
- Result types (return values) are still frozen dataclasses when multiple fields need to be returned
- Generate IDs with `uuid4()` at the application layer — not in the domain model constructor
- No mutable default arguments
