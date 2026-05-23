from datetime import datetime
from uuid import UUID

from backend.presentation.schema import Schema


class UserMeResponse(Schema):
    id: UUID
    name: str
    email: str
    created_at: datetime
    spotify_connected: bool
    spotify_premium: bool


class UserDeleteInformationResponse(Schema):
    session_count: int
