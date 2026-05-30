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

type _PlaylistDraftProvider = Callable[[], PlaylistDraft | None]


class MessageManager:
    _SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "system_prompt.md").read_text(
        encoding="utf-8"
    )
    _ONBOARDING_NUDGE_PROMPT = """\
You are now gathering context for a playlist. Ask 3-5 semantically relevant
clarifying questions based on the user's request. For every question, provide
3-8 concise, meaningful answer options. The UI offers a separate free-text
answer, so do not add a generic "Other" option. Topic guidance (NOT hardcoded -
choose what is relevant):
- Who is it for / what is the occasion?
- Which decades / eras?
- How broad or focused should the selection be?
- Mood / vibe?
- Any special requests?

Call `ask_onboarding_question` ONCE for each question.
Set `is_last_question=false` until the final question.
Set `is_last_question=true` only for the final question.
"""

    def __init__(
        self,
        system_prompt: str | None = None,
        phase: Phase = Phase.BUILD,
        playlist_draft_provider: _PlaylistDraftProvider | None = None,
        max_playlist_tracks: int = 75,
        history: list[Message] | None = None,
    ) -> None:
        self._system_prompt = system_prompt or self._SYSTEM_PROMPT
        self._phase = phase
        self._playlist_draft_provider = playlist_draft_provider
        self._max_playlist_tracks = max_playlist_tracks
        self._messages: list[Message] = []
        self.reset()
        if history:
            self._messages.extend(history)

    def all(self) -> list[Message]:
        messages: list[Message] = [SystemMessage(content=self._system_prompt)]
        self._inject_onboarding_nudge(messages)

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

    def _inject_onboarding_nudge(self, messages: list[Message]) -> None:
        if self._phase != Phase.ONBOARDING:
            return
        if self._has_any_onboarding_question_call():
            return
        self._inject_confirmed_context(messages, self._ONBOARDING_NUDGE_PROMPT)

    def _inject_confirmed_context(self, messages: list[Message], content: str) -> None:
        # Context Injection Pattern: UserMessage + AssistantMessage("Understood.")
        # Prevents consecutive UserMessages and ensures the model treats the
        # state as confirmed context rather than an open question.
        messages.append(UserMessage(content=content))
        messages.append(AssistantMessage(content="Understood."))

    def _has_any_onboarding_question_call(self) -> bool:
        for message in self._messages:
            if not isinstance(message, AssistantMessage):
                continue
            if not message.tool_calls:
                continue
            for tool_call in message.tool_calls:
                function_name = None
                function = getattr(tool_call, "function", None)
                if isinstance(function, dict):
                    function_name = function.get("name")
                else:
                    function_name = getattr(function, "name", None)
                if function_name == "ask_onboarding_question":
                    return True
        return False
