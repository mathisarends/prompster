from datetime import UTC, datetime
from uuid import UUID

import pytest

from backend.features.session.domain import (
    CompletedCall,
    FailedCall,
    PendingCall,
    ToolCallSequence,
    ToolFunction,
    is_pending,
)
from backend.features.session.domain.errors import (
    ToolCallAlreadyResolvedError,
    ToolCallNotFoundError,
)


def make_pending_call(call_id: str = "tc-1") -> PendingCall:
    return PendingCall(
        id=call_id,
        function=ToolFunction(name="search_track", arguments={"query": "electro"}),
    )


class TestSessionDomainToolCallSequence:
    def test_sequence_keeps_explicit_entity_identity(self) -> None:
        sequence_id = UUID(int=1)
        created_time = datetime(2026, 5, 5, tzinfo=UTC)

        sequence = ToolCallSequence.restore(
            calls=[make_pending_call()],
            id=sequence_id,
            created_at=created_time,
        )

        assert sequence.id == sequence_id
        assert sequence.created_at == created_time

    def test_resolve_replaces_pending_with_completed(self) -> None:
        sequence = ToolCallSequence.create(calls=[make_pending_call()])

        completed = sequence.resolve("tc-1", "done")

        assert isinstance(completed, CompletedCall)
        assert completed.result == "done"
        assert isinstance(sequence.calls[0], CompletedCall)

    def test_fail_replaces_pending_with_failed(self) -> None:
        sequence = ToolCallSequence.create(calls=[make_pending_call()])

        failed = sequence.fail("tc-1", "timeout")

        assert isinstance(failed, FailedCall)
        assert failed.error == "timeout"
        assert isinstance(sequence.calls[0], FailedCall)

    def test_is_complete_is_true_when_all_calls_are_resolved(self) -> None:
        first_call = make_pending_call(call_id="tc-1")
        second_call = make_pending_call(call_id="tc-2")
        sequence = ToolCallSequence.create(calls=[first_call, second_call])

        sequence.resolve("tc-1", "ok")
        sequence.fail("tc-2", "timeout")

        assert sequence.is_complete is True

    def test_add_appends_pending_call(self) -> None:
        sequence = ToolCallSequence.create(calls=[])

        appended = sequence.add(make_pending_call("tc-1"))

        assert appended.id == "tc-1"
        assert len(sequence.calls) == 1

    def test_remove_last_pending_removes_latest_unresolved_call(self) -> None:
        sequence = ToolCallSequence.create(
            calls=[
                make_pending_call("tc-1"),
                make_pending_call("tc-2"),
            ]
        )
        sequence.resolve("tc-1", "ok")

        removed = sequence.remove_last_pending()

        assert removed is not None
        assert removed.id == "tc-2"
        assert [call.id for call in sequence.calls] == ["tc-1"]


class TestToolCallSequenceResolution:
    def test_resolve_returns_completed_variant(self) -> None:
        sequence = ToolCallSequence.create(calls=[make_pending_call("tc-1")])

        completed = sequence.resolve("tc-1", "done")

        assert isinstance(completed, CompletedCall)
        assert completed.result == "done"

    def test_fail_returns_failed_variant(self) -> None:
        sequence = ToolCallSequence.create(calls=[make_pending_call("tc-1")])

        failed = sequence.fail("tc-1", "timeout")

        assert isinstance(failed, FailedCall)
        assert failed.error == "timeout"

    def test_resolve_raises_when_already_resolved(self) -> None:
        sequence = ToolCallSequence.create(calls=[make_pending_call("tc-1")])
        sequence.resolve("tc-1", "ok")

        with pytest.raises(ToolCallAlreadyResolvedError, match="already"):
            sequence.resolve("tc-1", "again")

    def test_pending_calls_filters_unresolved(self) -> None:
        sequence = ToolCallSequence.create(
            calls=[make_pending_call("tc-1"), make_pending_call("tc-2")],
        )
        sequence.resolve("tc-2", "ok")

        pending = sequence.pending_calls

        assert len(pending) == 1
        assert pending[0].id == "tc-1"
        assert is_pending(pending[0])
        assert sequence.is_complete is False

    def test_resolve_unknown_raises(self) -> None:
        sequence = ToolCallSequence.create(calls=[make_pending_call("tc-1")])

        with pytest.raises(ToolCallNotFoundError, match="No tool call"):
            sequence.resolve("tc-404", "nope")
