from datetime import datetime
from uuid import UUID

from backend.presentation.schema import Schema


class UserMeResponse(Schema):
    id: UUID
    name: str
    email: str
    created_at: datetime
