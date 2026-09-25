import pytest

from backend.features.session.domain.exceptions import (
    ToolCallAlreadyResolvedError,
    ToolCallNotFoundError,
)
from backend.features.session.domain import (
    CompletedCall,
    FailedCall,
    PendingCall,
    Phase,
    ToolCallSequence,
    ToolFunction,
    is_pending,
)


def make_pending(call_id: str) -> PendingCall:
    return PendingCall(
        id=call_id,
        function=ToolFunction(name="fetch_tracks", arguments={"limit": 5}),
    )


class TestSessionDomainToolCall:
    def test_phase_values_match_persisted_agent_contract(self) -> None:
        assert Phase.ONBOARDING == "onboarding"
        assert Phase.BUILD == "build"

    def test_resolve_returns_completed_variant(self) -> None:
        sequence = ToolCallSequence.create(calls=[make_pending("tc-1")])

        completed = sequence.resolve("tc-1", "done")

        assert isinstance(completed, CompletedCall)
        assert completed.result == "done"

    def test_fail_returns_failed_variant(self) -> None:
        sequence = ToolCallSequence.create(calls=[make_pending("tc-1")])

        failed = sequence.fail("tc-1", "timeout")

        assert isinstance(failed, FailedCall)
        assert failed.error == "timeout"

    def test_resolve_raises_when_already_resolved(self) -> None:
        sequence = ToolCallSequence.create(calls=[make_pending("tc-1")])
        sequence.resolve("tc-1", "ok")

        with pytest.raises(ToolCallAlreadyResolvedError, match="already"):
            sequence.resolve("tc-1", "again")

    def test_pending_calls_filters_unresolved(self) -> None:
        sequence = ToolCallSequence.create(
            calls=[make_pending("tc-1"), make_pending("tc-2")],
        )
        sequence.resolve("tc-2", "ok")

        pending = sequence.pending_calls

        assert len(pending) == 1
        assert pending[0].id == "tc-1"
        assert is_pending(pending[0])
        assert sequence.is_complete is False

    def test_resolve_unknown_raises(self) -> None:
        sequence = ToolCallSequence.create(calls=[make_pending("tc-1")])

        with pytest.raises(ToolCallNotFoundError, match="No tool call"):
            sequence.resolve("tc-404", "nope")
