from datetime import datetime
from uuid import UUID

from backend.presentation.schema import Schema


class UserMeResponse(Schema):
    id: UUID
    name: str
    created_at: datetime
    spotify_connected: bool
    spotify_premium: bool
    message_rate_limit: "UserMessageRateLimitResponse"


class UserDeleteInformationResponse(Schema):
    session_count: int


class UserMessageRateLimitResponse(Schema):
    limit: int
    remaining: int
    reset_at: datetime
