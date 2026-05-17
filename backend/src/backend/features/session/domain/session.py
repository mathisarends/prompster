from datetime import datetime
from typing import Self
from uuid import UUID

from backend.features.session.domain.exceptions import (
    NoCurrentAssistantMessageError,
    NoPendingToolCallGroupError,
    PendingToolCallsError,
    PlaylistTrackNotFoundError,
    SessionAccessDeniedError,
)
from backend.features.session.domain.playlist import Playlist, PlaylistTrack
from backend.features.session.domain.views import (
    MessageRole,
    SessionMessage,
    ToolCall,
    ToolCallGroup,
)
from backend.shared.ddd import Aggregate


class Session(Aggregate):
    def __init__(
        self,
        title: str,
        messages: list[SessionMessage],
        owner_id: UUID,
        playlist: Playlist | None = None,
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        self._title = title
        self._messages = messages
        self._owner_id = owner_id
        self._playlist = playlist

    @property
    def title(self) -> str:
        return self._title

    @property
    def owner_id(self) -> UUID:
        return self._owner_id

    @property
    def messages(self) -> tuple[SessionMessage, ...]:
        return tuple(self._messages)

    @property
    def playlist(self) -> Playlist | None:
        return self._playlist

    @classmethod
    def create_with_initial_prompt(
        cls,
        *,
        title: str,
        initial_prompt: str,
        owner_id: UUID,
    ) -> Self:
        session = cls(
            title=title,
            messages=[],
            owner_id=owner_id,
        )
        session.add_user_message(content=initial_prompt)
        return session

    def set_playlist(
        self,
        tracks: list[PlaylistTrack],
        name: str | None = None,
    ) -> Playlist:
        self._playlist = Playlist(tracks=tracks, name=name)
        return self._playlist

    def add_track(
        self,
        title: str,
        artist: str,
        year: int | None = None,
        cover_url: str | None = None,
    ) -> PlaylistTrack:
        if self._playlist is None:
            self._playlist = Playlist(tracks=[])
        track = PlaylistTrack(
            title=title,
            artist=artist,
            year=year,
            cover_url=cover_url,
        )
        self._playlist.tracks.append(track)
        return track

    def remove_track(self, track_id: UUID) -> None:
        if self._playlist is None:
            raise PlaylistTrackNotFoundError(f"Session {self.id} has no playlist.")
        for index, track in enumerate(self._playlist.tracks):
            if track.id == track_id:
                self._playlist.tracks.pop(index)
                return
        raise PlaylistTrackNotFoundError(
            f"Track {track_id} not found in playlist {self._playlist.id}."
        )

    def add_user_message(self, content: str) -> SessionMessage:
        if self._find_pending_tool_call_group() is not None:
            raise PendingToolCallsError(
                f"Cannot add user message to session {self.id} "
                "while tool calls are pending."
            )
        message = SessionMessage(role=MessageRole.USER, content=content)
        self._messages.append(message)
        return message

    def add_assistant_message(
        self,
        content: str = "",
        tool_calls: list[ToolCall] | None = None,
    ) -> SessionMessage:
        group = ToolCallGroup(calls=tool_calls) if tool_calls else None
        message = SessionMessage(
            role=MessageRole.ASSISTANT,
            content=content,
            tool_call_group=group,
        )
        self._messages.append(message)
        return message

    def append_to_current_assistant_message(self, chunk: str) -> SessionMessage:
        message = self._require_current_assistant_message()
        message.content += chunk
        return message

    def cancel_current_assistant_message(self) -> SessionMessage:
        message = self._require_current_assistant_message()
        self._messages.pop()
        return message

    def resolve_tool_call(self, tool_call_id: str, result: str) -> ToolCall:
        group = self._require_pending_group()
        return group.resolve(tool_call_id, result)

    def fail_tool_call(self, tool_call_id: str, error: str) -> ToolCall:
        group = self._require_pending_group()
        return group.fail(tool_call_id, error)

    def has_access(self, user_id: UUID) -> None:
        if self.owner_id != user_id:
            raise SessionAccessDeniedError(
                f"User {user_id} does not have access to session {self.id}."
            )

    def _require_pending_group(self) -> ToolCallGroup:
        group = self._find_pending_tool_call_group()
        if group is None:
            raise NoPendingToolCallGroupError(
                f"Session {self.id} has no pending tool call group."
            )
        return group

    def _find_pending_tool_call_group(self) -> ToolCallGroup | None:
        for message in reversed(self._messages):
            group = message.tool_call_group
            if group is not None and not group.is_complete:
                return group
        return None

    def _require_current_assistant_message(self) -> SessionMessage:
        if not self._messages or self._messages[-1].role != MessageRole.ASSISTANT:
            raise NoCurrentAssistantMessageError(
                f"Session {self.id} has no current assistant message."
            )
        return self._messages[-1]
