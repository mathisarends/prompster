from abc import ABC, abstractmethod
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class SessionExpiredError(Exception):
    pass


class SessionInvalidError(Exception):
    pass


class AuthSession(BaseModel):
    access_token: str
    refresh_token: str


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class TokenPayload(BaseModel):
    user_id: UUID
    expires_at: datetime


class TokenIssuer(ABC):
    @abstractmethod
    def create_session(self, user_id: UUID) -> AuthSession: ...

    @abstractmethod
    def validate(
        self,
        token: str,
        expected_type: TokenType = TokenType.ACCESS,
    ) -> TokenPayload: ...
