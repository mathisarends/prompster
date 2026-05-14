---
name: fastapi-orval
description: >
  Write FastAPI route handlers that are fully compatible with orval client generation,
  using Dishka for dependency injection. Use this skill whenever writing FastAPI endpoints
  that will be consumed by a TypeScript/Angular frontend via orval, openapi-typescript,
  or any OpenAPI-based client generator. Triggers on phrases like "FastAPI route", "orval",
  "OpenAPI client", "typed API", "generate client", or whenever writing new FastAPI endpoints
  for a frontend that uses generated clients. Always use Dishka (FromDishka / inject) instead
  of FastAPI Depends() for services.
---

# FastAPI Routes for Orval (Dishka DI)

Orval generates TypeScript clients from OpenAPI schemas. For clean generation every route needs:

- Explicit `operation_id` (becomes the function name in the client)
- Full response model typing (no `dict`, no `Any`)
- Typed path/query/body params with Pydantic models
- Correct status codes declared

DI is handled by **Dishka** — never use `Depends()` for services.

---

## Golden Rules

1. **`operation_id` is the contract** — it becomes the TS function name. Use `verb_noun` snake_case: `get_card`, `create_hitster_card`, `delete_playlist`.
2. **Never return `dict`** — always a typed Pydantic response model.
3. **Always declare `responses`** for non-200 codes orval needs to know about.
4. **One router per domain** — keeps generated TS hooks namespaced cleanly.
5. **Services via `FromDishka`** — path/query/body params stay as plain annotations; only injected services use `FromDishka`.

---

## Dishka Setup

```python
# providers/card_provider.py
from dishka import Provider, Scope, provide
from app.services.card_service import CardService
from app.repositories.card_repository import CardRepository

class CardProvider(Provider):
    scope = Scope.REQUEST

    @provide
    async def card_service(self, repo: CardRepository) -> CardService:
        return CardService(repo)
```

```python
# main.py
from dishka import make_async_container
from dishka.integrations.fastapi import setup_dishka
from app.providers.card_provider import CardProvider
from app.providers.db_provider import DatabaseProvider

app = FastAPI(title="Prompster API", version="1.0.0")

container = make_async_container(DatabaseProvider(), CardProvider())
setup_dishka(container, app)

app.include_router(cards.router, prefix="/api/v1")
```

---

## Route Anatomy

```python
from dishka.integrations.fastapi import FromDishka

@router.get(
    "/{card_id}",
    response_model=CardResponse,           # → TS return type
    status_code=200,
    operation_id="get_card",               # → function name in client
    responses={404: {"model": ErrorResponse}},  # → typed error in client
)
async def get_card(
    card_id: UUID,                         # path param — plain annotation
    service: FromDishka[CardService],      # injected by Dishka
) -> CardResponse:
    return await service.get(card_id)
```

---

## Pydantic Models

Always use `model_config` for consistent JSON output:

```python
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime

class CardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    artist: str
    year: int
    spotify_uri: str | None = None
    created_at: datetime

class CardCreateRequest(BaseModel):
    title: str
    artist: str
    year: int
    spotify_uri: str | None = None

class ErrorResponse(BaseModel):
    detail: str

class CardListResponse(BaseModel):
    items: list[CardResponse]
    total: int
    limit: int
    offset: int
```

---

## CRUD Example (full router)

```python
# api/routers/cards.py
from fastapi import APIRouter, HTTPException, status
from dishka.integrations.fastapi import FromDishka
from uuid import UUID
from app.schemas.card import CardResponse, CardCreateRequest, CardListResponse
from app.schemas.common import ErrorResponse
from app.services.card_service import CardService

router = APIRouter(prefix="/cards", tags=["cards"])


@router.get(
    "",
    response_model=CardListResponse,
    operation_id="list_cards",
)
async def list_cards(
    limit: int = 20,
    offset: int = 0,
    service: FromDishka[CardService] = ...,
) -> CardListResponse:
    return await service.list(limit=limit, offset=offset)


@router.get(
    "/{card_id}",
    response_model=CardResponse,
    operation_id="get_card",
    responses={404: {"model": ErrorResponse}},
)
async def get_card(
    card_id: UUID,
    service: FromDishka[CardService] = ...,
) -> CardResponse:
    card = await service.get(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return card


@router.post(
    "",
    response_model=CardResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_card",
)
async def create_card(
    body: CardCreateRequest,
    service: FromDishka[CardService] = ...,
) -> CardResponse:
    return await service.create(body)


@router.delete(
    "/{card_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_card",
    responses={404: {"model": ErrorResponse}},
)
async def delete_card(
    card_id: UUID,
    service: FromDishka[CardService] = ...,
) -> None:
    deleted = await service.delete(card_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Card not found")
```

> **Note:** `= ...` as default for `FromDishka` params is the idiomatic pattern —
> it signals "required, filled by container" without using `Depends()`.

---

## Pagination via Query Params

```python
from typing import Annotated
from fastapi import Query

class PaginationParams(BaseModel):
    limit: int = 20
    offset: int = 0

@router.get("", response_model=CardListResponse, operation_id="list_cards")
async def list_cards(
    pagination: Annotated[PaginationParams, Query()],
    service: FromDishka[CardService] = ...,
) -> CardListResponse: ...
```

---

## Auth: Current User via Dishka

Authenticated user injection belongs in a Dishka provider, not a `Depends`:

```python
# providers/auth_provider.py
from dishka import Provider, Scope, provide
from fastapi import Request, HTTPException
from app.services.jwt_service import JwtService
from app.domain.user import User

class AuthProvider(Provider):
    scope = Scope.REQUEST

    @provide
    async def current_user(self, request: Request, jwt: JwtService) -> User:
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return await jwt.decode(token)
```

```python
# In router — no Depends, no Security()
@router.get("/me", response_model=UserResponse, operation_id="get_current_user")
async def get_me(user: FromDishka[User] = ...) -> UserResponse:
    return UserResponse.model_validate(user)
```

---

## orval.config.ts (minimal)

```ts
import { defineConfig } from "orval";

export default defineConfig({
  prompster: {
    input: "http://localhost:8000/openapi.json",
    output: {
      mode: "tags-split", // one file per tag
      target: "src/api/generated",
      client: "angular", // or 'react-query', 'axios'
      prettier: true,
    },
  },
});
```

`operation_id: "get_card"` → generated as `getCard()` in TS.

---

## Common Mistakes

| Problem                        | Fix                                                                   |
| ------------------------------ | --------------------------------------------------------------------- |
| `response_model` missing       | orval generates `unknown` return type                                 |
| `operation_id` missing         | orval auto-generates ugly names like `get_api_v1_cards__card_id__get` |
| returning `dict`               | loses all type info                                                   |
| bare list response             | use wrapper object with `items: list[...]`                            |
| no 404 in `responses`          | error type is `unknown` in client                                     |
| using `Depends()` for services | bypasses Dishka container lifecycle/scoping                           |
