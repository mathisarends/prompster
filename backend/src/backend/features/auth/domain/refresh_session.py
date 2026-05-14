from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(slots=True, frozen=True)
class RefreshSession:
    token: str
    user_id: UUID
    expires_at: datetime
