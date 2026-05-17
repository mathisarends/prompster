from datetime import datetime, timezone
from uuid import uuid4

from backend.features.session.domain import (
    FollowUpOption,
    FollowUpQuestion,
    FollowUpQuestionGroup,
    MessageRole,
    SessionMessage,
    ToolCall,
    ToolCallGroup,
    ToolFunction,
)


def make_follow_up_question(label: str = "House") -> FollowUpQuestion:
    return FollowUpQuestion(
        question="Welches Genre?",
        options=[
            FollowUpOption(id="house", label=label),
            FollowUpOption(id="techno", label="Techno"),
        ],
    )


def make_tool_call(call_id: str = "tc-1") -> ToolCall:
    return ToolCall(
        id=call_id,
        function=ToolFunction(name="search_track", arguments={"query": "electro"}),
    )


class TestSessionDomainSessionMessage:
    def test_session_message_keeps_explicit_entity_identity(self) -> None:
        message_id = uuid4()
        created_time = datetime(2026, 6, 6, tzinfo=timezone.utc)

        message = SessionMessage(
            role=MessageRole.ASSISTANT,
            content="Noch eine Frage",
            id=message_id,
            created_time=created_time,
        )

        assert message.id == message_id
        assert message.created_at == created_time

    def test_session_message_keeps_role_content_and_groups(self) -> None:
        tool_call_group = ToolCallGroup(calls=[make_tool_call()])
        follow_up_group = FollowUpQuestionGroup(questions=[make_follow_up_question()])

        message = SessionMessage(
            role=MessageRole.ASSISTANT,
            content="Noch eine Frage",
            tool_call_group=tool_call_group,
            follow_up_group=follow_up_group,
        )

        assert message.role == MessageRole.ASSISTANT
        assert message.content == "Noch eine Frage"
        assert message.tool_call_group is tool_call_group
        assert message.follow_up_group is follow_up_group
