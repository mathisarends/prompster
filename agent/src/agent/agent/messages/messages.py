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
from agent.playlist import PlaylistDraft

_SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "system_prompt.md").read_text(
    encoding="utf-8"
)

type PlaylistDraftProvider = Callable[[], PlaylistDraft | None]
type UserEventsProvider = Callable[[], UserEvents]


class MessageManager:
    def __init__(
        self,
        system_prompt: str | None = None,
        playlist_draft_provider: PlaylistDraftProvider | None = None,
        user_events_provider: UserEventsProvider | None = None,
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
        return [SystemMessage(content=self._compose_system_prompt()), *self._messages]

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

    def _compose_system_prompt(self) -> str:
        return "\n\n".join(
            [
                self._system_prompt,
                "<context>",
                self._render_created_playlist_context(),
                self._render_user_events_context(),
                self._render_history_context(),
                "</context>",
            ]
        )

    def _render_created_playlist_context(self) -> str:
        playlist_draft = (
            self._playlist_draft_provider()
            if self._playlist_draft_provider is not None
            else None
        )

        lines = ["<created_playlist>"]
        if playlist_draft is None:
            lines.append("<exists>false</exists>")
            lines.append("</created_playlist>")
            return "\n".join(lines)

        lines.extend(
            [
                "<exists>true</exists>",
                f"<id>{playlist_draft.id}</id>",
                f"<name>{escape(playlist_draft.name)}</name>",
                f"<track_count>{len(playlist_draft.tracks)}</track_count>",
            ]
        )
        for index, track in enumerate(playlist_draft.tracks, start=1):
            track_text = (
                f"{escape(track.artist)} - {escape(track.title)}"
                if track.year is None
                else f"{escape(track.artist)} - {escape(track.title)} ({track.year})"
            )
            lines.append(
                f'<track index="{index}" id="{track.id}" pinned="{str(track.is_pinned).lower()}">{track_text}</track>'
            )

        lines.append("</created_playlist>")
        return "\n".join(lines)

    def _render_user_events_context(self) -> str:
        user_events = self._get_user_events()

        lines = ["<user_events>"]
        if not user_events:
            lines.append("<exists>false</exists>")
            lines.append("</user_events>")
            return "\n".join(lines)

        lines.extend(
            [
                "<exists>true</exists>",
                f"<event_count>{len(user_events)}</event_count>",
            ]
        )

        for index, event in enumerate(user_events, start=1):
            lines.append(self._render_user_event_entry(event=event, index=index))

        lines.append("</user_events>")
        return "\n".join(lines)

    def _render_history_context(self) -> str:
        entries: list[str] = []
        history_messages = self._get_history_messages()

        events_by_history_index: dict[int, list[UserEvent]] = {}
        for event in self._get_user_events():
            history_index = (
                event.history_index
                if event.history_index is not None
                else len(history_messages)
            )
            history_index = max(0, min(history_index, len(history_messages)))
            events_by_history_index.setdefault(history_index, []).append(event)

        for index, history_message in enumerate(history_messages):
            for event in events_by_history_index.get(index, []):
                entries.append(self._render_history_event_entry(event=event))
            entries.append(
                self._render_history_entry(
                    role=history_message["role"],
                    content=history_message["content"],
                )
            )

        for event in events_by_history_index.get(len(history_messages), []):
            entries.append(self._render_history_event_entry(event=event))

        if not entries:
            return "<history>\n<empty>true</empty>\n</history>"

        return "<history>\n" + "\n".join(entries) + "\n</history>"

    def _get_user_events(self) -> UserEvents:
        return (
            self._user_events_provider()
            if self._user_events_provider is not None
            else []
        )

    def _get_history_messages(self) -> list[dict[str, str]]:
        history_messages: list[dict[str, str]] = []
        for message in self._messages:
            if isinstance(message, UserMessage):
                history_messages.append({"role": "user", "content": message.content})
            elif isinstance(message, AssistantMessage) and message.content.strip():
                history_messages.append(
                    {"role": "assistant", "content": message.content}
                )
        return history_messages

    def _render_user_event_entry(self, *, event: UserEvent, index: int) -> str:
        return (
            f'<event index="{index}" type="{escape(event.type, quote=True)}" '
            f'at="{escape(event.occurred_at.isoformat(), quote=True)}">'
            f"{escape(event.label)}</event>"
        )

    def _render_history_event_entry(self, *, event: UserEvent) -> str:
        return (
            f'<event type="{escape(event.type, quote=True)}" '
            f'at="{escape(event.occurred_at.isoformat(), quote=True)}">'
            f"{escape(event.label)}</event>"
        )

    def _render_history_entry(self, *, role: str, content: str) -> str:
        escaped_lines = escape(content).splitlines() or [""]
        lines = [f'<message role="{role}">']
        lines.extend(escaped_lines)
        lines.append("</message>")
        return "\n".join(lines)
