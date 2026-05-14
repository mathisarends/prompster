from datetime import datetime, timezone
from uuid import UUID, uuid4


class Entity:
    def __init__(
        self, id: UUID | None = None, created_time: datetime | None = None
    ) -> None:
        self.id: UUID = id or uuid4()
        self.created_at: datetime = created_time or datetime.now(timezone.utc)


# semantic sugar
Aggregate = Entity
