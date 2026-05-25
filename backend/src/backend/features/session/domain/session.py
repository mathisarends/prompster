from datetime import datetime
from typing import Self
from uuid import UUID

from backend.features.session.domain.exceptions import (
    NoCurrentAssistantMessageError,
    NoPendingFollowUpGroupError,
    NoPendingToolCallSequenceError,
    PendingFollowUpQuestionsError,
    PendingToolCallsError,
    PlaylistTrackPinnedError,
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
    ToolCallSequence,
    UserMessage,
    UserMessageAttachment,
    WorkspaceEvent,
    WorkspaceEventType,
)
from backend.shared.ddd import Aggregate


class Session(Aggregate):
    def __init__(
        self,
        title: str,
        entries: list[SessionEntry],
        owner_id: UUID,
        is_starred: bool = False,
        playlist: Playlist | None = None,
        workspace_events: list[WorkspaceEvent] | None = None,
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        self._title = title
        self._entries = entries
        self._owner_id = owner_id
        self._is_starred = is_starred
        self._playlist = playlist
        self._workspace_events: list[WorkspaceEvent] = workspace_events or []

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
    def is_starred(self) -> bool:
        return self._is_starred

    @property
    def entries(self) -> tuple[SessionEntry, ...]:
        return tuple(self._entries)

    @property
    def playlist(self) -> Playlist | None:
        return self._playlist

    @property
    def workspace_events(self) -> tuple[WorkspaceEvent, ...]:
        return tuple(self._workspace_events)

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
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> Playlist:
        self._assert_pinned_tracks_preserved(tracks)
        self._playlist = Playlist(
            id=id,
            tracks=tracks,
            name=name,
            created_time=created_time,
        )
        return self._playlist

    def add_tracks(self, tracks: list[PlaylistTrack]) -> Playlist:
        if self._playlist is None:
            self._playlist = Playlist(tracks=[])
        self._playlist.tracks.extend(tracks)
        return self._playlist

    def add_track(
        self,
        title: str,
        artist: str,
        year: int | None = None,
        spotify_uri: str | None = None,
        cover_url: str | None = None,
        is_pinned: bool = True,
    ) -> PlaylistTrack:
        if self._playlist is None:
            self._playlist = Playlist(tracks=[])
        track = PlaylistTrack(
            title=title,
            artist=artist,
            year=year,
            spotify_uri=spotify_uri,
            cover_url=cover_url,
            is_pinned=is_pinned,
        )
        self._playlist.tracks.append(track)
        self._record_event(WorkspaceEventType.TRACK_ADDED, track)
        return track

    def remove_track(self, track_id: UUID) -> None:
        if self._playlist is None:
            raise PlaylistTrackNotFoundError(f"Session {self.id} has no playlist.")
        for index, track in enumerate(self._playlist.tracks):
            if track.id == track_id:
                self._playlist.tracks.pop(index)
                self._record_event(WorkspaceEventType.TRACK_REMOVED, track)
                return
        raise PlaylistTrackNotFoundError(
            f"Track {track_id} not found in playlist {self._playlist.id}."
        )

    def replace_track(self, track_id: UUID, track: PlaylistTrack) -> Playlist:
        if self._playlist is None:
            raise PlaylistTrackNotFoundError(f"Session {self.id} has no playlist.")
        for index, existing_track in enumerate(self._playlist.tracks):
            if existing_track.id == track_id:
                if existing_track.is_pinned:
                    raise PlaylistTrackPinnedError(
                        f"Track {track_id} is pinned and cannot be replaced."
                    )
                self._playlist.tracks[index] = track
                return self._playlist
        raise PlaylistTrackNotFoundError(
            f"Track {track_id} not found in playlist {self._playlist.id}."
        )

    def pin_track(self, track_id: UUID) -> PlaylistTrack:
        track = self._require_track(track_id)
        was_pinned = track.is_pinned
        track.is_pinned = True
        if not was_pinned:
            self._record_event(WorkspaceEventType.TRACK_PINNED, track)
        return track

    def unpin_track(self, track_id: UUID) -> PlaylistTrack:
        track = self._require_track(track_id)
        was_pinned = track.is_pinned
        track.is_pinned = False
        if was_pinned:
            self._record_event(WorkspaceEventType.TRACK_UNPINNED, track)
        return track

    @property
    def unconsumed_workspace_events(self) -> list[WorkspaceEvent]:
        return [event for event in self._workspace_events if not event.consumed]

    def require_track(self, track_id: UUID) -> PlaylistTrack:
        return self._require_track(track_id)

    def add_user_message(
        self,
        content: str,
        attachments: list[UserMessageAttachment] | None = None,
    ) -> UserMessage:
        if self._find_pending_tool_call_sequence() is not None:
            raise PendingToolCallsError(
                f"Cannot add user message to session {self.id} "
                "while tool calls are pending."
            )
        if self._find_pending_follow_up_group() is not None:
            raise PendingFollowUpQuestionsError(
                f"Cannot add user message to session {self.id} "
                "while follow-up questions are pending."
            )
        message = UserMessage(content=content, attachments=attachments)
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

    def add_tool_call(self, call: PendingCall) -> ToolCallSequence:
        last = self._entries[-1] if self._entries else None
        if isinstance(last, ToolCallSequence):
            last.add(call)
            return last
        sequence = ToolCallSequence(calls=[call])
        self._entries.append(sequence)
        return sequence

    def resolve_tool_call(self, tool_call_id: str, result: str) -> CompletedCall:
        sequence = self._require_pending_tool_call_sequence()
        return sequence.resolve(tool_call_id, result)

    def fail_tool_call(self, tool_call_id: str, error: str) -> FailedCall:
        sequence = self._require_pending_tool_call_sequence()
        return sequence.fail(tool_call_id, error)

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

    def _require_track(self, track_id: UUID) -> PlaylistTrack:
        if self._playlist is None:
            raise PlaylistTrackNotFoundError(f"Session {self.id} has no playlist.")
        for track in self._playlist.tracks:
            if track.id == track_id:
                return track
        raise PlaylistTrackNotFoundError(
            f"Track {track_id} not found in playlist {self._playlist.id}."
        )

    def _assert_pinned_tracks_preserved(self, tracks: list[PlaylistTrack]) -> None:
        if self._playlist is None:
            return

        candidate_by_id = {track.id: track for track in tracks}
        for existing_track in self._playlist.tracks:
            if not existing_track.is_pinned:
                continue
            candidate = candidate_by_id.get(existing_track.id)
            if candidate is None or not self._same_track(existing_track, candidate):
                raise PlaylistTrackPinnedError(
                    f"Track {existing_track.id} is pinned and cannot be replaced."
                )

    def _same_track(self, left: PlaylistTrack, right: PlaylistTrack) -> bool:
        return (
            left.id == right.id
            and left.title == right.title
            and left.artist == right.artist
            and left.year == right.year
            and left.spotify_uri == right.spotify_uri
            and left.cover_url == right.cover_url
            and left.is_pinned == right.is_pinned
        )

    def _record_event(
        self, event_type: WorkspaceEventType, track: PlaylistTrack
    ) -> WorkspaceEvent:
        event = WorkspaceEvent(
            event_type=event_type,
            track_id=track.id,
            track_title=track.title,
            track_artist=track.artist,
            track_spotify_uri=track.spotify_uri,
        )
        self._workspace_events.append(event)
        return event

    def pending_tool_call_sequence(self) -> ToolCallSequence | None:
        return self._find_pending_tool_call_sequence()

    def star(self) -> None:
        self._is_starred = True

    def unstar(self) -> None:
        self._is_starred = False

    def has_access(self, user_id: UUID) -> None:
        if self.owner_id != user_id:
            raise SessionAccessDeniedError(
                f"User {user_id} does not have access to session {self.id}."
            )

    def _require_pending_tool_call_sequence(self) -> ToolCallSequence:
        sequence = self._find_pending_tool_call_sequence()
        if sequence is None:
            raise NoPendingToolCallSequenceError(
                f"Session {self.id} has no pending tool call sequence."
            )
        return sequence

    def _find_pending_tool_call_sequence(self) -> ToolCallSequence | None:
        for entry in reversed(self._entries):
            if isinstance(entry, ToolCallSequence) and not entry.is_complete:
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
