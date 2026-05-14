from typing import Protocol
from uuid import UUID


class TokenGenerator(Protocol):
    def create_access_token(self, *, user_id: UUID) -> str: ...

    def create_refresh_token(self) -> str: ...
