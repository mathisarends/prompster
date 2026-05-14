from abc import ABC, abstractmethod
from uuid import UUID

from backend.features.auth.application.schemas import (
    AuthSession,
    TokenPayload,
    TokenType,
)


class PasswordHasher(ABC):
    @abstractmethod
    def hash(self, password: str) -> str: ...

    @abstractmethod
    def verify(self, password: str, hashed: str) -> bool: ...


class TokenIssuer(ABC):
    @abstractmethod
    def create_session(self, user_id: UUID) -> AuthSession: ...

    @abstractmethod
    def validate(
        self,
        token: str,
        expected_type: TokenType = TokenType.ACCESS,
    ) -> TokenPayload: ...
