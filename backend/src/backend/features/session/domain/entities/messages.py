from datetime import datetime
from uuid import UUID

from backend.shared.ddd import Entity


class UserMessage(Entity):
    def __init__(
        self,
        content: str,
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        self.content = content


class AssistantMessage(Entity):
    def __init__(
        self,
        content: str = "",
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        self.content = content
