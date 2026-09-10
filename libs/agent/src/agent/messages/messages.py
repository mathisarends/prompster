from collections.abc import Callable, Sequence
from pathlib import Path

from llmify import (
    AssistantMessage,
    Message,
    SystemMessage,
    ToolCall,
    ToolResultMessage,
    UserMessage,
)

from agent.views import UserEvent
from agent.deck import DeckDraft
from agent.tools.views import Phase
from .rendering import render_deck_context, render_user_message_content

type _DeckDraftProvider = Callable[[], DeckDraft | None]

_COMPACTED_MARKER = "[context-compacted]"
_COMPACTED_PLACEHOLDER = (
    f"{_COMPACTED_MARKER} Earlier results were elided to save context. "
    "Any tracks they returned are still in the workspace cache and can be "
    "added by URI; re-run the relevant search if you need the details again."
)

_PROMPTS_DIR = Path(__file__).parent / "prompts"
_SHARED_PROMPT = (_PROMPTS_DIR / "shared_system_prompt.md").read_text(encoding="utf-8")
_PHASE_PROMPTS: dict[Phase, str] = {
    Phase.ONBOARDING: (_PROMPTS_DIR / "onboarding_system_prompt.md").read_text(
        encoding="utf-8"
    ),
    Phase.BUILD: (_PROMPTS_DIR / "building_system_prompt.md").read_text(
        encoding="utf-8"
    ),
}


class MessageManager:
    def __init__(
        self,
        system_prompt: str | None = None,
        phase: Phase = Phase.BUILD,
        deck_draft_provider: _DeckDraftProvider | None = None,
        max_deck_tracks: int = 75,
        history: list[Message] | None = None,
    ) -> None:
        if system_prompt:
            self._system_prompt = system_prompt
        else:
            phase_prompt = _PHASE_PROMPTS.get(phase, "")
            self._system_prompt = f"{_SHARED_PROMPT}\n\n{phase_prompt}".strip()
        self._phase = phase
        self._deck_draft_provider = deck_draft_provider
        self._max_deck_tracks = max_deck_tracks
        self._messages: list[Message] = []
        self.reset()
        if history:
            self._messages.extend(history)

    def all(self) -> list[Message]:
        messages: list[Message] = [SystemMessage(content=self._system_prompt)]

        deck_context = self._render_deck_context()
        if deck_context is not None:
            self._inject_confirmed_context(messages, deck_context)

        messages.extend(self._messages)
        return messages

    def conversation_transcript(self, *, max_chars: int = 16000) -> str:
        """User and assistant turns as plain text, for downstream LLM context.

        Skips the system prompt, the injected deck context, tool calls, and tool
        results so a critic LLM sees what the user actually asked for. Keeps the
        most recent turns when the transcript would exceed ``max_chars``.
        """
        lines: list[str] = []
        for message in self._messages:
            match message:
                case UserMessage(content=str(content)) if content.strip():
                    lines.append(f"User: {content.strip()}")
                case AssistantMessage(content=str(content)) if content.strip():
                    lines.append(f"Assistant: {content.strip()}")
                case _:
                    continue
        transcript = "\n".join(lines)
        if len(transcript) > max_chars:
            transcript = "…\n" + transcript[-max_chars:]
        return transcript

    def add_user(
        self,
        content: str,
        curation_events: Sequence[UserEvent] | None = None,
    ) -> None:
        rendered = render_user_message_content(content, curation_events)
        self._messages.append(UserMessage(content=rendered))

    def add_assistant(
        self, content: str, tool_calls: list[ToolCall] | None = None
    ) -> None:
        self._messages.append(
            AssistantMessage(content=content, tool_calls=tool_calls or [])
        )

    def add_tool_result(self, tool_call_id: str, content: str) -> None:
        self._messages.append(
            ToolResultMessage(tool_call_id=tool_call_id, content=content)
        )

    def compact_tool_results(self, *, keep_last: int = 4) -> int:
        """Elide the content of older tool-result messages to reclaim context.

        Tool results (Spotify search / playlist track dumps) accumulate in the
        history and are the dominant source of context growth in a long build
        loop. They are safe to drop: the deck state is re-rendered fresh on
        every :meth:`all` call and every track stays in the ``DeckStore`` cache
        keyed by URI, so the model can still add cached tracks and re-search if
        it needs detail again. The most recent ``keep_last`` results are left
        intact so the model keeps its immediate working set.

        Returns the number of tool results that were compacted this call.
        """
        tool_result_indices = [
            index
            for index, message in enumerate(self._messages)
            if isinstance(message, ToolResultMessage)
        ]
        if len(tool_result_indices) <= keep_last:
            return 0

        compacted = 0
        for index in tool_result_indices[:-keep_last]:
            message = self._messages[index]
            assert isinstance(message, ToolResultMessage)
            if message.content.startswith(_COMPACTED_MARKER):
                continue
            self._messages[index] = ToolResultMessage(
                tool_call_id=message.tool_call_id,
                content=_COMPACTED_PLACEHOLDER,
            )
            compacted += 1
        return compacted

    def reset(self) -> None:
        self._messages = []

    def _render_deck_context(self) -> str | None:
        deck_draft = (
            self._deck_draft_provider()
            if self._deck_draft_provider is not None
            else None
        )
        if deck_draft is None:
            return None
        return render_deck_context(deck_draft, max_tracks=self._max_deck_tracks)

    def _inject_confirmed_context(self, messages: list[Message], content: str) -> None:
        # Context Injection Pattern: UserMessage + AssistantMessage("Understood.")
        # Prevents consecutive UserMessages and ensures the model treats the
        # state as confirmed context rather than an open question.
        messages.append(UserMessage(content=content))
        messages.append(AssistantMessage(content="Understood."))
