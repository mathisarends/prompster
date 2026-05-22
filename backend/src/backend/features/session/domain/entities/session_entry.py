from backend.features.session.domain.entities.follow_up_question_group import (
    FollowUpQuestionGroup,
)
from backend.features.session.domain.entities.messages import (
    AssistantMessage,
    UserMessage,
)
from backend.features.session.domain.entities.tool_call_sequence import ToolCallSequence


type SessionEntry = (
    UserMessage | AssistantMessage | ToolCallSequence | FollowUpQuestionGroup
)
