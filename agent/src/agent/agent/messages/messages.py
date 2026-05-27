from collections.abc import Callable
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

from agent.agent.views import UserEvent, UserEvents
from agent.playlist import PlaylistDraft, PlaylistDraftTrack

_SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "system_prompt.md").read_text(
    encoding="utf-8"
)

type _PlaylistDraftProvider = Callable[[], PlaylistDraft | None]
type _UserEventsProvider = Callable[[], UserEvents]


class MessageManager:
    def __init__(
        self,
        system_prompt: str | None = None,
        playlist_draft_provider: _PlaylistDraftProvider | None = None,
        user_events_provider: _UserEventsProvider | None = None,
        history: list[Message] | None = None,
    ) -> None:
        self._system_prompt = system_prompt or _SYSTEM_PROMPT
        self._playlist_draft_provider = playlist_draft_provider
        self._user_events_provider = user_events_provider
        self._messages: list[Message] = []
        self.reset()
        if history:
            self._messages.extend(history)

    def all(self) -> list[Message]:
        messages: list[Message] = [SystemMessage(content=self._system_prompt)]

        playlist_context = self._render_playlist_context()
        if playlist_context is not None:
            # Context Injection Pattern: UserMessage + AssistantMessage("Understood.")
            # Prevents consecutive UserMessages and ensures the model treats the
            # state as confirmed context rather than an open question.
            messages.append(UserMessage(content=playlist_context))
            messages.append(AssistantMessage(content="Understood."))

        messages.extend(self._messages_with_injected_user_events())
        return messages

    def add_user(self, content: str) -> None:
        self._messages.append(UserMessage(content=content))

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

        lines = [
            (
                f'<created_playlist id="{playlist_draft.id}" '
                f'name="{escape(playlist_draft.name, quote=True)}" '
                f'track_count="{len(playlist_draft.tracks)}" '
                'pinned_tracks="hard_constraints">'
            ),
        ]
        lines.extend(
            self._render_playlist_track(track) for track in playlist_draft.tracks
        )
        lines.append("</created_playlist>")
        return "\n".join(lines)

    def _render_playlist_track(self, track: PlaylistDraftTrack) -> str:
        attrs = [
            f'id="{track.id}"',
            f'label="{self._render_track_label(track)}"',
        ]
        if track.is_pinned:
            attrs.append('pinned="true"')
        return f"<track {' '.join(attrs)} />"

    def _render_track_label(self, track: PlaylistDraftTrack) -> str:
        label = f"{track.artist} - {track.title}"
        if track.year is not None:
            label = f"{label} ({track.year})"
        return escape(label, quote=True)

    def _get_user_events(self) -> UserEvents:
        return (
            self._user_events_provider()
            if self._user_events_provider is not None
            else []
        )

    def _messages_with_injected_user_events(self) -> list[Message]:
        history_count = self._count_history_messages()
        events_by_history_index = self._group_user_events_by_history_index(
            history_count=history_count
        )

        messages: list[Message] = []
        history_index = 0

        for message in self._messages:
            pending_events = events_by_history_index.get(history_index, [])

            if pending_events and isinstance(message, UserMessage):
                # Append events to the next real UserMessage —
                # prevents consecutive UserMessages from separate event messages.
                event_block = "\n".join(
                    self._render_user_event_entry(e) for e in pending_events
                )
                messages.append(
                    UserMessage(content=f"{event_block}\n\n{message.content}")
                )
            else:
                if pending_events:
                    # Should not happen (events always land before a UserMessage),
                    # but as a fallback: emit events as a separate UserMessage before the turn.
                    event_block = "\n".join(
                        self._render_user_event_entry(e) for e in pending_events
                    )
                    messages.append(UserMessage(content=event_block))
                messages.append(message)

            if self._is_history_message(message):
                history_index += 1

        # Trailing events ohne nachfolgende Message (am Ende der History)
        for event in events_by_history_index.get(history_index, []):
            messages.append(UserMessage(content=self._render_user_event_entry(event)))

        return messages

    def _count_history_messages(self) -> int:
        return sum(1 for message in self._messages if self._is_history_message(message))

    def _group_user_events_by_history_index(
        self, *, history_count: int
    ) -> dict[int, list[UserEvent]]:
        events_by_history_index: dict[int, list[UserEvent]] = {}
        for event in self._get_user_events():
            history_index = (
                event.history_index
                if event.history_index is not None
                else history_count
            )
            history_index = max(0, min(history_index, history_count))
            events_by_history_index.setdefault(history_index, []).append(event)
        return events_by_history_index

    def _is_history_message(self, message: Message) -> bool:
        if isinstance(message, UserMessage):
            return True
        return isinstance(message, AssistantMessage) and bool(message.content.strip())

    def _render_user_event_entry(self, event: UserEvent) -> str:
        return (
            f'<event type="{escape(event.type, quote=True)}" '
            f'at="{escape(event.occurred_at.isoformat(), quote=True)}">'
            f"{escape(event.label)}</event>"
        )
