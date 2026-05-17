from abc import ABC, abstractmethod
from uuid import UUID

from backend.features.auth.application.schemas import (
    AuthSession,
    GoogleIdentity,
    TokenPayload,
    TokenType,
)


class GoogleOAuthProvider(ABC):
    @abstractmethod
    def build_authorization_url(self, *, state: str) -> str: ...

    @abstractmethod
    async def exchange_code_for_identity(
        self,
        *,
        authorization_code: str,
    ) -> GoogleIdentity: ...


class TokenIssuer(ABC):
    @abstractmethod
    def create_session(self, user_id: UUID) -> AuthSession: ...

    @abstractmethod
    def validate(
        self,
        token: str,
        expected_type: TokenType = TokenType.ACCESS,
    ) -> TokenPayload: ...
