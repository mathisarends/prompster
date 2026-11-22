from agent.messages import conversation_transcript
from harnessed.models import AssistantMessage, ToolCall, ToolMessage, UserMessage


def test_transcript_keeps_only_user_and_assistant_text() -> None:
    call = ToolCall("search_tracks", {"query": "abba"}, id="call-1")

    transcript = conversation_transcript(
        [
            UserMessage("Nur ABBA bitte"),
            AssistantMessage("", (call,)),
            ToolMessage("result", tool_call_id="call-1"),
            AssistantMessage("Mache ich"),
        ]
    )

    assert transcript == "User: Nur ABBA bitte\nAssistant: Mache ich"


def test_long_transcript_keeps_the_most_recent_text() -> None:
    transcript = conversation_transcript(
        [UserMessage("alt " * 20), UserMessage("neu")],
        max_chars=12,
    )

    assert transcript.startswith("…\n")
    assert transcript.endswith("User: neu")
