from datetime import datetime
from typing import Self
from uuid import UUID

from backend.features.session.domain.exceptions import (
    NoCurrentAssistantMessageError,
    NoPendingFollowUpGroupError,
    NoPendingToolCallGroupError,
    PendingFollowUpQuestionsError,
    PendingToolCallsError,
    PlaylistTrackNotFoundError,
    SessionAccessDeniedError,
)
from backend.features.session.domain.entities import (
    AssistantMessage,
    CompletedCall,
    FailedCall,
    FollowUpQuestion,
    FollowUpQuestionGroup,
    PendingCall,
    Playlist,
    PlaylistTrack,
    SessionEntry,
    ToolCallGroup,
    UserMessage,
)
from backend.shared.ddd import Aggregate


class Session(Aggregate):
    def __init__(
        self,
        title: str,
        entries: list[SessionEntry],
        owner_id: UUID,
        playlist: Playlist | None = None,
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        self._title = title
        self._entries = entries
        self._owner_id = owner_id
        self._playlist = playlist

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        self._title = value

    @property
    def owner_id(self) -> UUID:
        return self._owner_id

    @property
    def entries(self) -> tuple[SessionEntry, ...]:
        return tuple(self._entries)

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
            entries=[],
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

    def add_user_message(self, content: str) -> UserMessage:
        if self._find_pending_tool_call_group() is not None:
            raise PendingToolCallsError(
                f"Cannot add user message to session {self.id} "
                "while tool calls are pending."
            )
        if self._find_pending_follow_up_group() is not None:
            raise PendingFollowUpQuestionsError(
                f"Cannot add user message to session {self.id} "
                "while follow-up questions are pending."
            )
        message = UserMessage(content=content)
        self._entries.append(message)
        return message

    def add_assistant_message(self, content: str = "") -> AssistantMessage:
        message = AssistantMessage(content=content)
        self._entries.append(message)
        return message

    def append_to_current_assistant_message(self, chunk: str) -> AssistantMessage:
        message = self._require_current_assistant_message()
        message.content += chunk
        return message

    def cancel_current_assistant_message(self) -> AssistantMessage:
        message = self._require_current_assistant_message()
        self._entries.pop()
        return message

    def add_tool_call(self, call: PendingCall) -> ToolCallGroup:
        last = self._entries[-1] if self._entries else None
        if isinstance(last, ToolCallGroup):
            last.add(call)
            return last
        group = ToolCallGroup(calls=[call])
        self._entries.append(group)
        return group

    def resolve_tool_call(self, tool_call_id: str, result: str) -> CompletedCall:
        group = self._require_pending_tool_call_group()
        return group.resolve(tool_call_id, result)

    def fail_tool_call(self, tool_call_id: str, error: str) -> FailedCall:
        group = self._require_pending_tool_call_group()
        return group.fail(tool_call_id, error)

    def add_follow_up_questions(
        self, questions: list[FollowUpQuestion]
    ) -> FollowUpQuestionGroup:
        group = FollowUpQuestionGroup(questions=questions)
        self._entries.append(group)
        return group

    def answer_follow_up_with_option(
        self, question_id: UUID, option_id: str
    ) -> FollowUpQuestion:
        group = self._require_pending_follow_up_group()
        return group.answer_with_option(question_id, option_id)

    def answer_follow_up_with_text(
        self, question_id: UUID, text: str
    ) -> FollowUpQuestion:
        group = self._require_pending_follow_up_group()
        return group.answer_with_text(question_id, text)

    def skip_follow_up(self, question_id: UUID) -> FollowUpQuestion:
        group = self._require_pending_follow_up_group()
        return group.skip(question_id)

    def skip_remaining_follow_ups(
        self, question_id: UUID
    ) -> tuple[FollowUpQuestion, ...]:
        group = self._require_pending_follow_up_group()
        return tuple(group.skip_remaining_from(question_id))

    def pending_follow_up_group(self) -> FollowUpQuestionGroup | None:
        return self._find_pending_follow_up_group()

    def require_pending_follow_up_group(self) -> FollowUpQuestionGroup:
        return self._require_pending_follow_up_group()

    def pending_tool_call_group(self) -> ToolCallGroup | None:
        return self._find_pending_tool_call_group()

    def has_access(self, user_id: UUID) -> None:
        if self.owner_id != user_id:
            raise SessionAccessDeniedError(
                f"User {user_id} does not have access to session {self.id}."
            )

    def _require_pending_tool_call_group(self) -> ToolCallGroup:
        group = self._find_pending_tool_call_group()
        if group is None:
            raise NoPendingToolCallGroupError(
                f"Session {self.id} has no pending tool call group."
            )
        return group

    def _find_pending_tool_call_group(self) -> ToolCallGroup | None:
        for entry in reversed(self._entries):
            if isinstance(entry, ToolCallGroup) and not entry.is_complete:
                return entry
        return None

    def _require_pending_follow_up_group(self) -> FollowUpQuestionGroup:
        group = self._find_pending_follow_up_group()
        if group is None:
            raise NoPendingFollowUpGroupError(
                f"Session {self.id} has no pending follow-up question group."
            )
        return group

    def _find_pending_follow_up_group(self) -> FollowUpQuestionGroup | None:
        for entry in reversed(self._entries):
            if isinstance(entry, FollowUpQuestionGroup) and not entry.is_complete:
                return entry
        return None

    def _require_current_assistant_message(self) -> AssistantMessage:
        if not self._entries or not isinstance(self._entries[-1], AssistantMessage):
            raise NoCurrentAssistantMessageError(
                f"Session {self.id} has no current assistant message."
            )
        return self._entries[-1]
