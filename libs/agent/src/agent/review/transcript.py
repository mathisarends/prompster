from collections.abc import Iterable

from harnessed.models import AssistantMessage, Message, UserMessage


def conversation_transcript(
    messages: Iterable[Message],
    *,
    max_chars: int = 16000,
) -> str:
    """User and assistant turns as plain text, for the deck critic.

    Tool calls and results are left out so the critic sees what the user asked
    for. Keeps the most recent turns when the transcript exceeds ``max_chars``.
    """
    lines: list[str] = []
    for message in messages:
        text = message.text.strip()
        if not text:
            continue
        match message:
            case UserMessage():
                lines.append(f"User: {text}")
            case AssistantMessage():
                lines.append(f"Assistant: {text}")
    transcript = "\n".join(lines)
    if len(transcript) > max_chars:
        return "…\n" + transcript[-max_chars:]
    return transcript
