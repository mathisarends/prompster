import pytest

from backend.features.session.domain.exceptions import (
    ToolCallAlreadyResolvedError,
    ToolCallNotFoundError,
)
from backend.features.session.domain.views import (
    ToolCall,
    ToolCallGroup,
    ToolCallState,
    ToolFunction,
)


def make_pending_call(call_id: str) -> ToolCall:
    return ToolCall(
        id=call_id,
        function=ToolFunction(name="fetch_tracks", arguments={"limit": 5}),
    )


class TestSessionDomainViews:
    def test_tool_call_complete_sets_completed_state(self) -> None:
        call = make_pending_call("tc-1")

        call.complete("done")

        assert call.state == ToolCallState.COMPLETED
        assert call.result == "done"
        assert call.is_resolved is True

    def test_tool_call_fail_sets_failed_state(self) -> None:
        call = make_pending_call("tc-1")

        call.fail("timeout")

        assert call.state == ToolCallState.FAILED
        assert call.error == "timeout"
        assert call.is_resolved is True

    def test_tool_call_complete_raises_when_already_resolved(self) -> None:
        call = make_pending_call("tc-1")
        call.complete("ok")

        with pytest.raises(ToolCallAlreadyResolvedError, match="already"):
            call.complete("again")

    def test_tool_call_group_pending_calls_filters_unresolved(self) -> None:
        pending_call = make_pending_call("tc-1")
        resolved_call = make_pending_call("tc-2")
        resolved_call.complete("ok")
        group = ToolCallGroup(calls=[pending_call, resolved_call])

        pending = group.pending_calls

        assert len(pending) == 1
        assert pending[0] is pending_call
        assert group.is_complete is False

    def test_tool_call_group_resolve_unknown_raises(self) -> None:
        group = ToolCallGroup(calls=[make_pending_call("tc-1")])

        with pytest.raises(ToolCallNotFoundError, match="No tool call"):
            group.resolve("tc-404", "nope")
