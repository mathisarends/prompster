from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class UserMeResponse(BaseModel):
    id: UUID
    name: str
    email: str
    created_at: datetime
