from collections.abc import Callable, Sequence
from html import escape
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
from agent.messages.rendering import render_track_tag
from .rendering import render_user_message_content

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / name).read_text(encoding="utf-8")


_PERSONA = _load_prompt("persona.md")
_BUILD_SYSTEM_PROMPT = f"{_PERSONA}\n\n{_load_prompt('build_workflow.md')}"
_ONBOARDING_SYSTEM_PROMPT = (
    f"{_PERSONA}\n\n{_load_prompt('onboarding_system_prompt.md')}"
)

type _PlaylistDraftProvider = Callable[[], PlaylistDraft | None]
type _PhaseProvider = Callable[[], Phase]


class MessageManager:
    def __init__(
        self,
        system_prompt: str | None = None,
        phase_provider: _PhaseProvider | None = None,
        playlist_draft_provider: _PlaylistDraftProvider | None = None,
        max_playlist_tracks: int = 75,
        history: list[Message] | None = None,
    ) -> None:
        self._system_prompt_override = system_prompt
        self._phase_provider = phase_provider
        self._playlist_draft_provider = playlist_draft_provider
        self._max_playlist_tracks = max_playlist_tracks
        self._messages: list[Message] = []
        self.reset()
        if history:
            self._messages.extend(history)

    def all(self) -> list[Message]:
        messages: list[Message] = [SystemMessage(content=self._resolve_system_prompt())]

        playlist_context = self._render_playlist_context()
        if playlist_context is not None:
            # Context Injection Pattern: UserMessage + AssistantMessage("Understood.")
            # Prevents consecutive UserMessages and ensures the model treats the
            # state as confirmed context rather than an open question.
            messages.append(UserMessage(content=playlist_context))
            messages.append(AssistantMessage(content="Understood."))

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

    def _resolve_system_prompt(self) -> str:
        if self._system_prompt_override is not None:
            return self._system_prompt_override
        phase = self._phase_provider() if self._phase_provider is not None else None
        if phase == Phase.ONBOARDING:
            return _ONBOARDING_SYSTEM_PROMPT
        return _BUILD_SYSTEM_PROMPT

    def _render_playlist_context(self) -> str | None:
        playlist_draft = (
            self._playlist_draft_provider()
            if self._playlist_draft_provider is not None
            else None
        )
        if playlist_draft is None:
            return None

        track_count = len(playlist_draft.tracks)
        remaining_tracks = max(0, self._max_playlist_tracks - track_count)
        lines = [
            (
                f'<created_playlist id="{playlist_draft.id}" '
                f'name="{escape(playlist_draft.name, quote=True)}" '
                f'track_count="{track_count}" '
                f'max_tracks="{self._max_playlist_tracks}" '
                f'remaining_tracks="{remaining_tracks}" '
                'pinned_tracks="hard_constraints">'
            ),
        ]
        lines.extend(
            render_track_tag(track, include_pinned=True)
            for track in playlist_draft.tracks
        )
        lines.append("</created_playlist>")
        return "\n".join(lines)
