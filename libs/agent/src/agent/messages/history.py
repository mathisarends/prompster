"""Turn the persisted conversation into a harnessed ``SessionState``.

The backend rebuilds the history from its domain entries on every run, so what
happens here decides how much context each run starts with. Track results from
earlier runs are reduced to stable digests: their URIs are no longer in the
run's track cache, and identical digests keep the provider's prompt cache valid
from one run to the next.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass, replace
from html import unescape

from harnessed.models import (
    AssistantMessage,
    Message,
    ToolMessage,
    UserMessage,
)
from harnessed.sessions import SessionState
from harnessed.sessions.state import HistoryEntry, HistoryStep, HistoryTurn

CONTINUE_PROMPT = "Continue from where the conversation left off."

_TRACK_RESULT_TOOLS = frozenset({"search_tracks", "get_spotify_playlist_tracks"})
_TRACK_LABEL = re.compile(r'<track\b[^>]*\blabel="([^"]*)"')
_ARCHIVED_HEADER = (
    "[Archived result from an earlier run. These URIs have expired, "
    "so search again before adding one of these tracks.]"
)


@dataclass(frozen=True, slots=True)
class ReplayedConversation:
    state: SessionState
    run_input: UserMessage


def replay_history(
    history: Sequence[Message],
    *,
    new_input: str | None = None,
) -> ReplayedConversation:
    """Split ``history`` into prior state and the input that starts this run.

    Without ``new_input``, the trailing user message is the run's input, because
    the backend persists it before starting the agent.
    """
    messages = list(history)
    if new_input is not None:
        run_input = UserMessage(new_input)
    elif messages and isinstance(messages[-1], UserMessage):
        run_input = messages.pop()
    else:
        run_input = UserMessage(CONTINUE_PROMPT)
    return ReplayedConversation(
        state=_to_session_state(_to_answered_messages(messages)),
        run_input=run_input,
    )


def digest_track_result(content: str) -> str:
    """Keep what the model saw, without URIs that can no longer be added."""
    labels = [unescape(label) for label in _TRACK_LABEL.findall(content)]
    if not labels:
        return content
    return "\n".join([_ARCHIVED_HEADER, *labels])


def _to_answered_messages(history: Sequence[Message]) -> list[Message]:
    """Keep only tool calls that have a matching result.

    A cancelled run can leave calls without results, which providers reject.
    """
    answered: list[Message] = []
    index = 0
    while index < len(history):
        message = history[index]
        index += 1
        match message:
            case UserMessage():
                answered.append(message)
            case AssistantMessage():
                results: list[ToolMessage] = []
                while index < len(history) and isinstance(history[index], ToolMessage):
                    results.append(history[index])
                    index += 1
                answered.extend(_to_assistant_batch(message, results))
    return answered


def _to_assistant_batch(
    message: AssistantMessage,
    results: Sequence[ToolMessage],
) -> list[Message]:
    result_ids = {result.tool_call_id for result in results}
    calls = tuple(call for call in message.tool_calls if call.id in result_ids)
    if not message.content and not calls:
        return []

    batch: list[Message] = [replace(message, tool_calls=calls)]
    names = {call.id: call.name for call in calls}
    seen: set[str] = set()
    for result in results:
        if result.tool_call_id not in names or result.tool_call_id in seen:
            continue
        seen.add(result.tool_call_id)
        batch.append(_archive_result(result, tool_name=names[result.tool_call_id]))
    return batch


def _archive_result(result: ToolMessage, *, tool_name: str) -> ToolMessage:
    if tool_name not in _TRACK_RESULT_TOOLS or result.is_error:
        return result
    return replace(result, content=digest_track_result(result.text))


def _to_session_state(messages: Sequence[Message]) -> SessionState:
    entries: list[HistoryEntry] = []
    turns: list[HistoryTurn] = []
    steps: list[HistoryStep] = []
    turn_id: str | None = None
    step_start: int | None = None

    def close_step(boundary: int) -> None:
        nonlocal step_start
        if step_start is not None and turn_id is not None:
            steps.append(HistoryStep(turn_id, step_start, boundary))
        step_start = None

    def close_turn(boundary: int) -> None:
        close_step(boundary)
        if turn_id is not None:
            turns.append(HistoryTurn(turn_id, boundary))

    for position, message in enumerate(messages):
        is_input = isinstance(message, UserMessage)
        if is_input or turn_id is None:
            close_turn(position)
            turn_id = f"replay-{len(turns)}"
        if isinstance(message, AssistantMessage):
            close_step(position)
            step_start = position
        entries.append(
            HistoryEntry(position, message, turn_id=turn_id, is_input=is_input)
        )
    close_turn(len(messages))

    return SessionState(history=tuple(entries), turns=tuple(turns), steps=tuple(steps))
