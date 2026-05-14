from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class AuthSession(BaseModel):
    jwt_token: str
    refresh_token: str


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class TokenPayload(BaseModel):
    user_id: UUID
    email: str | None = None
    expires_at: datetime
