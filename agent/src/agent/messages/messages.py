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
from agent.playlist import PlaylistDraft
from agent.tools.views import Phase
from .rendering import render_playlist_context, render_user_message_content

type _PlaylistDraftProvider = Callable[[], PlaylistDraft | None]


class MessageManager:
    _SHARED_PROMPT = (
        Path(__file__).parent / "prompts" / "shared_system_prompt.md"
    ).read_text(encoding="utf-8")
    _PHASE_PROMPTS: dict[Phase, str] = {
        Phase.ONBOARDING: (
            Path(__file__).parent / "prompts" / "onboarding_system_prompt.md"
        ).read_text(encoding="utf-8"),
        Phase.BUILD: (
            Path(__file__).parent / "prompts" / "building_system_prompt.md"
        ).read_text(encoding="utf-8"),
    }

    def __init__(
        self,
        system_prompt: str | None = None,
        phase: Phase = Phase.BUILD,
        playlist_draft_provider: _PlaylistDraftProvider | None = None,
        max_playlist_tracks: int = 75,
        history: list[Message] | None = None,
    ) -> None:
        if system_prompt:
            self._system_prompt = system_prompt
        else:
            phase_prompt = self._PHASE_PROMPTS.get(phase, "")
            self._system_prompt = f"{self._SHARED_PROMPT}\n\n{phase_prompt}".strip()
        self._phase = phase
        self._playlist_draft_provider = playlist_draft_provider
        self._max_playlist_tracks = max_playlist_tracks
        self._messages: list[Message] = []
        self.reset()
        if history:
            self._messages.extend(history)

    def all(self) -> list[Message]:
        messages: list[Message] = [SystemMessage(content=self._system_prompt)]

        playlist_context = self._render_playlist_context()
        if playlist_context is not None:
            self._inject_confirmed_context(messages, playlist_context)

        messages.extend(self._messages)
        return messages

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

    def reset(self) -> None:
        self._messages = []

    def _render_playlist_context(self) -> str | None:
        playlist_draft = (
            self._playlist_draft_provider()
            if self._playlist_draft_provider is not None
            else None
        )
        if playlist_draft is None:
            return None
        return render_playlist_context(
            playlist_draft, max_tracks=self._max_playlist_tracks
        )

    def _inject_confirmed_context(self, messages: list[Message], content: str) -> None:
        # Context Injection Pattern: UserMessage + AssistantMessage("Understood.")
        # Prevents consecutive UserMessages and ensures the model treats the
        # state as confirmed context rather than an open question.
        messages.append(UserMessage(content=content))
        messages.append(AssistantMessage(content="Understood."))
