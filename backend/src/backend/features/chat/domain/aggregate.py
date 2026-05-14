from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ChatAggregate:
    id: UUID
    title: str
    system_prompt: str | None
    created_at: datetime
    updated_at: datetime
