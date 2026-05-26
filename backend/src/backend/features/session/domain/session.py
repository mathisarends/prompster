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
    UserCurationEventAlreadyConsumedError,
    UserCurationEventNotFoundError,
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
    UserCurationEvent,
    UserCurationEventType,
    UserMessage,
    UserMessageAttachment,
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
        user_curation_events: list[UserCurationEvent] | None = None,
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        self._title = title
        self._entries = entries
        self._owner_id = owner_id
        self._is_starred = is_starred
        self._playlist = playlist
        self._user_curation_events: list[UserCurationEvent] = user_curation_events or []

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
    def user_curation_events(self) -> tuple[UserCurationEvent, ...]:
        return tuple(self._user_curation_events)

    @property
    def unconsumed_user_curation_events(self) -> list[UserCurationEvent]:
        return [event for event in self._user_curation_events if not event.consumed]

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
        record_user_curation_event: bool = True,
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
        if record_user_curation_event:
            self._record_user_curation_event(UserCurationEventType.TRACK_ADDED, track)
        return track

    def remove_track(
        self, track_id: UUID, record_user_curation_event: bool = True
    ) -> None:
        if self._playlist is None:
            raise PlaylistTrackNotFoundError(f"Session {self.id} has no playlist.")
        for index, track in enumerate(self._playlist.tracks):
            if track.id == track_id:
                self._playlist.tracks.pop(index)
                if record_user_curation_event:
                    self._record_user_curation_event(
                        UserCurationEventType.TRACK_REMOVED,
                        track,
                    )
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

    def pin_track(
        self, track_id: UUID, record_user_curation_event: bool = True
    ) -> PlaylistTrack:
        track = self._require_track(track_id)
        was_pinned = track.is_pinned
        track.is_pinned = True
        if not was_pinned and record_user_curation_event:
            self._record_user_curation_event(UserCurationEventType.TRACK_PINNED, track)
        return track

    def unpin_track(
        self, track_id: UUID, record_user_curation_event: bool = True
    ) -> PlaylistTrack:
        track = self._require_track(track_id)
        was_pinned = track.is_pinned
        track.is_pinned = False
        if was_pinned and record_user_curation_event:
            self._record_user_curation_event(
                UserCurationEventType.TRACK_UNPINNED,
                track,
            )
        return track

    def require_track(self, track_id: UUID) -> PlaylistTrack:
        return self._require_track(track_id)

    def restore_user_curation_event(self, event_id: UUID) -> None:
        event = self._require_unconsumed_user_curation_event(event_id)
        self._apply_user_curation_event_reversal(event)
        self._user_curation_events.remove(event)
        self._detach_user_curation_event_from_messages(event_id=event.id)

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
        message = UserMessage(
            content=content,
            attachments=attachments,
            user_curation_events=self._unbound_unconsumed_user_curation_events(),
        )
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

    def _require_unconsumed_user_curation_event(
        self, event_id: UUID
    ) -> UserCurationEvent:
        for event in self._user_curation_events:
            if event.id != event_id:
                continue
            if event.consumed:
                raise UserCurationEventAlreadyConsumedError(
                    f"User curation event {event_id} has already been consumed "
                    "and cannot be restored."
                )
            return event
        raise UserCurationEventNotFoundError(
            f"User curation event {event_id} not found in session {self.id}."
        )

    def _apply_user_curation_event_reversal(self, event: UserCurationEvent) -> None:
        if event.event_type == UserCurationEventType.TRACK_PINNED:
            self.unpin_track(event.track_id, record_user_curation_event=False)
            return
        if event.event_type == UserCurationEventType.TRACK_UNPINNED:
            self.pin_track(event.track_id, record_user_curation_event=False)
            return
        if event.event_type == UserCurationEventType.TRACK_ADDED:
            self.remove_track(event.track_id, record_user_curation_event=False)
            return
        if event.event_type == UserCurationEventType.TRACK_REMOVED:
            self._restore_removed_track(event)
            return

    def _restore_removed_track(self, event: UserCurationEvent) -> PlaylistTrack:
        if self._playlist is None:
            self._playlist = Playlist(tracks=[])
        track = PlaylistTrack(
            id=event.track_id,
            title=event.track_title,
            artist=event.track_artist,
            spotify_uri=event.track_spotify_uri,
            cover_url=event.track_cover_url,
            is_pinned=False,
        )
        self._playlist.tracks.append(track)
        return track

    def _record_user_curation_event(
        self, event_type: UserCurationEventType, track: PlaylistTrack
    ) -> UserCurationEvent:
        event = UserCurationEvent(
            event_type=event_type,
            track_id=track.id,
            track_title=track.title,
            track_artist=track.artist,
            track_spotify_uri=track.spotify_uri,
            track_cover_url=track.cover_url,
            history_index=self._current_history_index(),
        )
        self._user_curation_events.append(event)
        self._bind_user_curation_event_to_message(event)
        return event

    def _bind_user_curation_event_to_message(self, event: UserCurationEvent) -> None:
        if self._is_user_curation_event_bound(event_id=event.id):
            return

        message = self._find_target_user_message_for_event(event)
        if message is None:
            return

        message.user_curation_events = (*message.user_curation_events, event)

    def _find_target_user_message_for_event(
        self, event: UserCurationEvent
    ) -> UserMessage | None:
        for entry in self._entries:
            if isinstance(entry, UserMessage) and entry.created_at >= event.created_at:
                return entry

        if event.history_index is None:
            return None

        return self._find_target_user_message_by_history_index(event.history_index)

    def _find_target_user_message_by_history_index(
        self, event_history_index: int
    ) -> UserMessage | None:
        history_index = 0
        for entry in self._entries:
            if isinstance(entry, UserMessage):
                if history_index >= event_history_index:
                    return entry
                history_index += 1
                continue
            if isinstance(entry, AssistantMessage) and entry.content.strip():
                history_index += 1
        return None

    def _is_user_curation_event_bound(self, *, event_id: UUID) -> bool:
        for entry in self._entries:
            if not isinstance(entry, UserMessage):
                continue
            if any(event.id == event_id for event in entry.user_curation_events):
                return True
        return False

    def _unbound_unconsumed_user_curation_events(self) -> list[UserCurationEvent]:
        return [
            event
            for event in self.unconsumed_user_curation_events
            if not self._is_user_curation_event_bound(event_id=event.id)
        ]

    def _detach_user_curation_event_from_messages(self, *, event_id: UUID) -> None:
        for entry in self._entries:
            if not isinstance(entry, UserMessage):
                continue
            if not entry.user_curation_events:
                continue

            remaining_events = tuple(
                event for event in entry.user_curation_events if event.id != event_id
            )
            if len(remaining_events) != len(entry.user_curation_events):
                entry.user_curation_events = remaining_events

    def _current_history_index(self) -> int:
        history_index = 0
        for entry in self._entries:
            if isinstance(entry, UserMessage):
                history_index += 1
                continue
            if isinstance(entry, AssistantMessage) and entry.content.strip():
                history_index += 1
        return history_index

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
