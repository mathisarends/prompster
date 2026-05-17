from datetime import datetime, timezone
from uuid import uuid4

from backend.features.session.domain import (
    ToolCall,
    ToolCallGroup,
    ToolCallState,
    ToolFunction,
)


def make_tool_call(call_id: str = "tc-1") -> ToolCall:
    return ToolCall(
        id=call_id,
        function=ToolFunction(name="search_track", arguments={"query": "electro"}),
    )


class TestSessionDomainToolCallGroup:
    def test_group_keeps_explicit_entity_identity(self) -> None:
        group_id = uuid4()
        created_time = datetime(2026, 5, 5, tzinfo=timezone.utc)

        group = ToolCallGroup(
            calls=[make_tool_call()],
            id=group_id,
            created_time=created_time,
        )

        assert group.id == group_id
        assert group.created_at == created_time

    def test_fail_marks_matching_tool_call_as_failed(self) -> None:
        call = make_tool_call()
        group = ToolCallGroup(calls=[call])

        failed = group.fail("tc-1", "timeout")

        assert failed is call
        assert failed.state == ToolCallState.FAILED
        assert failed.error == "timeout"

    def test_is_complete_is_true_when_all_calls_are_resolved(self) -> None:
        first_call = make_tool_call(call_id="tc-1")
        second_call = make_tool_call(call_id="tc-2")
        group = ToolCallGroup(calls=[first_call, second_call])

        first_call.complete("ok")
        second_call.fail("timeout")

        assert group.is_complete is True
