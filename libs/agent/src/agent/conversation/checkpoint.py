from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any

from harnessed.sessions import (
    SessionCheckpoint,
    SessionCommit,
    SessionExecution,
    SessionState,
)

type JSONObject = Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class AgentCheckpoint:
    """A saved conversation as two JSON documents.

    ``state`` is the settled history, including plugin values such as the deck
    catalog. ``execution`` is the open turn on top of it, or ``None`` when the
    conversation was idle. Together they reopen the agent where it stopped,
    also while it is paused.
    """

    state: JSONObject
    execution: JSONObject | None = None

    def restore(self) -> SessionState | SessionCheckpoint:
        state = SessionState.from_dict(self.state)
        if self.execution is None:
            return state
        return SessionCheckpoint.from_parts(
            state, SessionExecution.from_dict(self.execution)
        )


@dataclass(frozen=True, slots=True)
class AgentCommit:
    """One durable change: a new ``state`` only when history changed."""

    execution: JSONObject
    state: JSONObject | None = None

    @classmethod
    def from_session(cls, commit: SessionCommit) -> AgentCommit:
        checkpoint = commit.checkpoint
        return cls(
            execution=checkpoint.execution.to_dict(),
            state=checkpoint.state.to_dict() if commit.state_changed else None,
        )


type CommitSink = Callable[[AgentCommit], Awaitable[None]]
