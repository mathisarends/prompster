from agent.messages import digest_track_result, replay_history
from agent.messages.history import CONTINUE_PROMPT
from harnessed.models import (
    AssistantMessage,
    ToolCall,
    ToolMessage,
    ToolStatus,
    UserMessage,
)


def _messages(result) -> list:
    return [entry.message for entry in result.state.history]


def _search(call_id: str = "call-1") -> ToolCall:
    return ToolCall("search_tracks", {"query": "abba"}, id=call_id)


def test_trailing_user_message_becomes_the_run_input() -> None:
    replayed = replay_history([UserMessage("a"), AssistantMessage("b"), UserMessage("c")])

    assert replayed.run_input.text == "c"
    assert [message.text for message in _messages(replayed)] == ["a", "b"]


def test_new_input_keeps_the_whole_history() -> None:
    replayed = replay_history([UserMessage("a")], new_input="b")

    assert replayed.run_input.text == "b"
    assert [message.text for message in _messages(replayed)] == ["a"]


def test_history_ending_with_the_assistant_continues() -> None:
    replayed = replay_history([UserMessage("a"), AssistantMessage("b")])

    assert replayed.run_input.text == CONTINUE_PROMPT


def test_unanswered_tool_calls_are_dropped() -> None:
    replayed = replay_history(
        [UserMessage("a"), AssistantMessage("", (_search(),)), UserMessage("b")]
    )

    assert [type(message) for message in _messages(replayed)] == [UserMessage]


def test_partly_answered_calls_keep_only_the_answered_call() -> None:
    answered, cancelled = _search("call-1"), _search("call-2")

    replayed = replay_history(
        [
            UserMessage("a"),
            AssistantMessage("Suche", (answered, cancelled)),
            ToolMessage("x", tool_call_id="call-1"),
            UserMessage("b"),
        ]
    )

    assistant = _messages(replayed)[1]
    assert [call.id for call in assistant.tool_calls] == ["call-1"]


def test_orphan_tool_results_are_dropped() -> None:
    replayed = replay_history(
        [
            UserMessage("a"),
            ToolMessage("x", tool_call_id="missing"),
            UserMessage("b"),
        ]
    )

    assert [type(message) for message in _messages(replayed)] == [UserMessage]


def test_replayed_turns_and_steps_describe_the_history() -> None:
    replayed = replay_history(
        [
            UserMessage("a"),
            AssistantMessage("", (_search(),)),
            ToolMessage("x", tool_call_id="call-1"),
            AssistantMessage("fertig"),
            UserMessage("b"),
        ]
    )

    assert [turn.boundary for turn in replayed.state.turns] == [4]
    assert [(step.start, step.boundary) for step in replayed.state.steps] == [
        (1, 3),
        (3, 4),
    ]


def test_track_results_are_replayed_as_digests() -> None:
    content = (
        '<track uri="spotify:track:1" label="a-ha - Take On Me (1985)" />\n'
        '<track uri="spotify:track:2" label="Simon &amp; Garfunkel - Cecilia" />'
    )

    replayed = replay_history(
        [
            UserMessage("a"),
            AssistantMessage("", (_search(),)),
            ToolMessage(content, tool_call_id="call-1"),
            UserMessage("b"),
        ]
    )

    digest = _messages(replayed)[2].text
    assert "spotify:track" not in digest
    assert "a-ha - Take On Me (1985)" in digest
    assert "Simon & Garfunkel - Cecilia" in digest
    assert digest.startswith("[Archived result")


def test_failed_track_results_stay_verbatim() -> None:
    replayed = replay_history(
        [
            UserMessage("a"),
            AssistantMessage("", (_search(),)),
            ToolMessage(
                '<track uri="u" label="l" />',
                tool_call_id="call-1",
                status=ToolStatus.ERROR,
            ),
            UserMessage("b"),
        ]
    )

    assert _messages(replayed)[2].text == '<track uri="u" label="l" />'


def test_digest_is_stable_for_identical_results() -> None:
    content = '<track uri="u" label="A - B" />'

    assert digest_track_result(content) == digest_track_result(content)


def test_digest_leaves_results_without_tracks_untouched() -> None:
    assert digest_track_result("Keine Treffer.") == "Keine Treffer."
