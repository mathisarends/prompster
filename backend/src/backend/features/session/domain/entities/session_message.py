from datetime import datetime
from enum import StrEnum
from uuid import UUID

from backend.features.session.domain.entities.follow_up_question_group import (
    FollowUpQuestionGroup,
)
from backend.features.session.domain.entities.tool_call_group import ToolCallGroup
from backend.shared.ddd import Entity


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class SessionMessage(Entity):
    def __init__(
        self,
        role: MessageRole,
        content: str,
        tool_call_group: ToolCallGroup | None = None,
        follow_up_group: FollowUpQuestionGroup | None = None,
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        self.role = role
        self.content = content
        self.tool_call_group = tool_call_group
        self.follow_up_group = follow_up_group
