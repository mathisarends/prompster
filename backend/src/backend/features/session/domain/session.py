from datetime import datetime
from typing import Self
from uuid import UUID

from backend.features.session.domain.exceptions import (
    ArtistReferenceNotFoundError,
    InvalidSessionPhaseTransitionError,
    NoCurrentAssistantMessageError,
    NoPendingToolCallSequenceError,
    PendingToolCallsError,
    PlaylistTrackLimitExceededError,
    PlaylistTrackPinnedError,
    PlaylistTrackNotFoundError,
    PlaylistReferenceNotFoundError,
    SessionAccessDeniedError,
    UserCurationEventAlreadyConsumedError,
    UserCurationEventMissingTrackYearError,
    UserCurationEventNotFoundError,
)
from backend.features.session.domain.entities import (
    ArtistReference,
    AssistantMessage,
    CompletedCall,
    FailedCall,
    PendingCall,
    Playlist,
    PlaylistReference,
    PlaylistTrack,
    SessionEntry,
    ToolCallSequence,
    UserCurationEvent,
    UserCurationEventType,
    UserMessage,
    UserMessageAttachment,
)
from backend.features.session.domain.views import Phase
from backend.shared.ddd import Aggregate

MAX_PLAYLIST_TRACKS = 50


class Session(Aggregate):
    def __init__(
        self,
        title: str,
        entries: list[SessionEntry],
        owner_id: UUID,
        is_starred: bool = False,
        playlist: Playlist | None = None,
        user_curation_events: list[UserCurationEvent] | None = None,
        playlist_references: list[PlaylistReference] | None = None,
        artist_references: list[ArtistReference] | None = None,
        phase: Phase = Phase.BUILD,
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
        self._playlist_references: list[PlaylistReference] = playlist_references or []
        self._artist_references: list[ArtistReference] = artist_references or []
        self._phase = phase
        if self._playlist is not None:
            self._assert_track_limit(total_tracks=len(self._playlist.tracks))

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
    def phase(self) -> Phase:
        return self._phase

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
    def playlist_references(self) -> tuple[PlaylistReference, ...]:
        return tuple(self._playlist_references)

    @property
    def artist_references(self) -> tuple[ArtistReference, ...]:
        return tuple(self._artist_references)

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
        self._assert_track_limit(total_tracks=len(tracks))
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
        self._assert_track_limit(total_tracks=len(self._playlist.tracks) + len(tracks))
        self._playlist.tracks.extend(tracks)
        return self._playlist

    def add_track(
        self,
        title: str,
        artist: str,
        year: int,
        spotify_uri: str | None = None,
        cover_url: str | None = None,
        is_pinned: bool = True,
        record_user_curation_event: bool = True,
    ) -> PlaylistTrack:
        if self._playlist is None:
            self._playlist = Playlist(tracks=[])
        self._assert_track_limit(total_tracks=len(self._playlist.tracks) + 1)
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

    def add_playlist_reference(
        self,
        *,
        spotify_playlist_id: str,
        name: str,
        owner: str | None = None,
        cover_url: str | None = None,
        total_tracks: int | None = None,
    ) -> PlaylistReference:
        for reference in self._playlist_references:
            if reference.spotify_playlist_id != spotify_playlist_id:
                continue
            reference.name = name
            reference.owner = owner
            reference.cover_url = cover_url
            reference.total_tracks = total_tracks
            return reference

        reference = PlaylistReference(
            spotify_playlist_id=spotify_playlist_id,
            name=name,
            owner=owner,
            cover_url=cover_url,
            total_tracks=total_tracks,
        )
        self._playlist_references.append(reference)
        return reference

    def add_artist_reference(
        self,
        *,
        spotify_artist_id: str,
        name: str,
        image_url: str | None = None,
        genres: tuple[str, ...] = (),
        followers: int | None = None,
        popularity: int | None = None,
    ) -> ArtistReference:
        for reference in self._artist_references:
            if reference.spotify_artist_id != spotify_artist_id:
                continue
            reference.name = name
            reference.image_url = image_url
            reference.genres = tuple(genres)
            reference.followers = followers
            reference.popularity = popularity
            return reference

        reference = ArtistReference(
            spotify_artist_id=spotify_artist_id,
            name=name,
            image_url=image_url,
            genres=genres,
            followers=followers,
            popularity=popularity,
        )
        self._artist_references.append(reference)
        return reference

    def remove_playlist_reference(self, reference_id: UUID) -> None:
        for index, reference in enumerate(self._playlist_references):
            if reference.id == reference_id:
                self._playlist_references.pop(index)
                return
        raise PlaylistReferenceNotFoundError(
            f"Playlist reference {reference_id} not found in session {self.id}."
        )

    def remove_artist_reference(self, reference_id: UUID) -> None:
        for index, reference in enumerate(self._artist_references):
            if reference.id == reference_id:
                self._artist_references.pop(index)
                return
        raise ArtistReferenceNotFoundError(
            f"Artist reference {reference_id} not found in session {self.id}."
        )

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

    def remove_last_pending_tool_call(self) -> PendingCall | None:
        sequence = self._find_pending_tool_call_sequence()
        if sequence is None:
            return None

        removed = sequence.remove_last_pending()
        if removed is not None and not sequence.calls:
            self._entries.remove(sequence)
        return removed

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
        self._assert_track_limit(total_tracks=len(self._playlist.tracks) + 1)
        if event.track_year is None:
            raise UserCurationEventMissingTrackYearError(
                f"User curation event {event.id} cannot restore track "
                f"{event.track_id} because track_year is missing."
            )
        track = PlaylistTrack(
            id=event.track_id,
            title=event.track_title,
            artist=event.track_artist,
            year=event.track_year,
            spotify_uri=event.track_spotify_uri,
            cover_url=event.track_cover_url,
            is_pinned=False,
        )
        self._playlist.tracks.append(track)
        return track

    def _assert_track_limit(self, *, total_tracks: int) -> None:
        if total_tracks <= MAX_PLAYLIST_TRACKS:
            return
        raise PlaylistTrackLimitExceededError(
            f"Session {self.id} already has {MAX_PLAYLIST_TRACKS} tracks."
        )

    def _record_user_curation_event(
        self, event_type: UserCurationEventType, track: PlaylistTrack
    ) -> UserCurationEvent:
        event = UserCurationEvent(
            event_type=event_type,
            track_id=track.id,
            track_title=track.title,
            track_artist=track.artist,
            track_year=track.year,
            track_spotify_uri=track.spotify_uri,
            track_cover_url=track.cover_url,
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

    def pending_tool_call_sequence(self) -> ToolCallSequence | None:
        return self._find_pending_tool_call_sequence()

    def star(self) -> None:
        self._is_starred = True

    def unstar(self) -> None:
        self._is_starred = False

    def advance_to_building_phase(self) -> None:
        if self._phase != Phase.ONBOARDING:
            raise InvalidSessionPhaseTransitionError(
                f"Cannot advance session {self.id} from {self._phase} to {Phase.BUILD}."
            )
        self._phase = Phase.BUILD

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

    def _require_current_assistant_message(self) -> AssistantMessage:
        if not self._entries or not isinstance(self._entries[-1], AssistantMessage):
            raise NoCurrentAssistantMessageError(
                f"Session {self.id} has no current assistant message."
            )
        return self._entries[-1]
