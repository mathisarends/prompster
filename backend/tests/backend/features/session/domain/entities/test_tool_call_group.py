from datetime import datetime, timezone
from uuid import uuid4

from backend.features.session.domain import (
    CompletedCall,
    FailedCall,
    PendingCall,
    ToolCallGroup,
    ToolFunction,
)


def make_pending_call(call_id: str = "tc-1") -> PendingCall:
    return PendingCall(
        id=call_id,
        function=ToolFunction(name="search_track", arguments={"query": "electro"}),
    )


class TestSessionDomainToolCallGroup:
    def test_group_keeps_explicit_entity_identity(self) -> None:
        group_id = uuid4()
        created_time = datetime(2026, 5, 5, tzinfo=timezone.utc)

        group = ToolCallGroup(
            calls=[make_pending_call()],
            id=group_id,
            created_time=created_time,
        )

        assert group.id == group_id
        assert group.created_at == created_time

    def test_resolve_replaces_pending_with_completed(self) -> None:
        group = ToolCallGroup(calls=[make_pending_call()])

        completed = group.resolve("tc-1", "done")

        assert isinstance(completed, CompletedCall)
        assert completed.result == "done"
        assert isinstance(group.calls[0], CompletedCall)

    def test_fail_replaces_pending_with_failed(self) -> None:
        group = ToolCallGroup(calls=[make_pending_call()])

        failed = group.fail("tc-1", "timeout")

        assert isinstance(failed, FailedCall)
        assert failed.error == "timeout"
        assert isinstance(group.calls[0], FailedCall)

    def test_is_complete_is_true_when_all_calls_are_resolved(self) -> None:
        first_call = make_pending_call(call_id="tc-1")
        second_call = make_pending_call(call_id="tc-2")
        group = ToolCallGroup(calls=[first_call, second_call])

        group.resolve("tc-1", "ok")
        group.fail("tc-2", "timeout")

        assert group.is_complete is True

    def test_add_appends_pending_call(self) -> None:
        group = ToolCallGroup(calls=[])

        appended = group.add(make_pending_call("tc-1"))

        assert appended.id == "tc-1"
        assert len(group.calls) == 1
