from collections.abc import Sequence
from datetime import UTC, datetime
import hashlib
import json
from typing import Self
from uuid import UUID, uuid4

from backend.features.session.domain.exceptions import (
    ArtistReferenceNotFoundError,
    InvalidSessionPhaseTransitionError,
    NoCurrentAssistantMessageError,
    NoPendingToolCallSequenceError,
    PendingToolCallsError,
    PlaylistTrackLimitExceededError,
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
    ImageAttachment,
    OnboardingQuestion,
    OnboardingQuestionSelectionMode,
    PendingCall,
    Playlist,
    PlaylistReference,
    PlaylistTrack,
    SessionEntry,
    ToolCallSequence,
    ToolResultItem,
    UserCurationEvent,
    UserCurationEventType,
    UserMessage,
    UserMessageAttachment,
)
from backend.features.session.domain.views import Phase
from backend.shared.ddd import Aggregate

MAX_PLAYLIST_TRACKS = 50
PLAYLIST_FINGERPRINT_VERSION = 1
DECIDE_FOR_ME_OPTION = "Entscheide für mich"


class Session(Aggregate):
    def __init__(
        self,
        *,
        id: UUID,
        created_at: datetime,
        title: str,
        entries: list[SessionEntry],
        owner_id: UUID,
        is_starred: bool = False,
        playlist: Playlist | None = None,
        user_curation_events: list[UserCurationEvent] | None = None,
        playlist_references: list[PlaylistReference] | None = None,
        artist_references: list[ArtistReference] | None = None,
        phase: Phase = Phase.ONBOARDING,
        onboarding_questions: list[OnboardingQuestion] | None = None,
        playlist_pdf_storage_key: str | None = None,
        playlist_pdf_fingerprint: str | None = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at)
        self._title = title
        self._entries = entries
        self._owner_id = owner_id
        self._is_starred = is_starred
        self._playlist = playlist
        self._user_curation_events: list[UserCurationEvent] = user_curation_events or []
        self._playlist_references: list[PlaylistReference] = playlist_references or []
        self._artist_references: list[ArtistReference] = artist_references or []
        self._phase = phase
        self._onboarding_questions: list[OnboardingQuestion] = (
            onboarding_questions or []
        )
        self._playlist_pdf_storage_key = playlist_pdf_storage_key
        self._playlist_pdf_fingerprint = playlist_pdf_fingerprint

        if self._playlist is not None:
            self._assert_track_limit(total_tracks=len(self._playlist.tracks))

    @classmethod
    def create(cls, *, owner_id: UUID, title: str = "") -> Self:
        return cls(
            id=uuid4(),
            created_at=datetime.now(UTC),
            title=title,
            entries=[],
            owner_id=owner_id,
        )

    @classmethod
    def restore(
        cls,
        *,
        id: UUID,
        created_at: datetime,
        title: str,
        entries: list[SessionEntry],
        owner_id: UUID,
        is_starred: bool = False,
        playlist: Playlist | None = None,
        user_curation_events: list[UserCurationEvent] | None = None,
        playlist_references: list[PlaylistReference] | None = None,
        artist_references: list[ArtistReference] | None = None,
        phase: Phase = Phase.ONBOARDING,
        onboarding_questions: list[OnboardingQuestion] | None = None,
        playlist_pdf_storage_key: str | None = None,
        playlist_pdf_fingerprint: str | None = None,
    ) -> Self:
        return cls(
            id=id,
            created_at=created_at,
            title=title,
            entries=entries,
            owner_id=owner_id,
            is_starred=is_starred,
            playlist=playlist,
            user_curation_events=user_curation_events,
            playlist_references=playlist_references,
            artist_references=artist_references,
            phase=phase,
            onboarding_questions=onboarding_questions,
            playlist_pdf_storage_key=playlist_pdf_storage_key,
            playlist_pdf_fingerprint=playlist_pdf_fingerprint,
        )

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
    def playlist_pdf_storage_key(self) -> str | None:
        return self._playlist_pdf_storage_key

    @property
    def playlist_pdf_fingerprint(self) -> str | None:
        return self._playlist_pdf_fingerprint

    @property
    def playlist_fingerprint(self) -> str | None:
        if self._playlist is None:
            return None
        payload = {
            "version": PLAYLIST_FINGERPRINT_VERSION,
            "tracks": [
                {
                    "title": track.title,
                    "artist": track.artist,
                    "year": track.year,
                    "spotify_uri": track.spotify_uri,
                }
                for track in self._playlist.tracks
            ],
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def set_playlist_pdf_export(
        self,
        *,
        storage_key: str,
        fingerprint: str,
    ) -> None:
        self._playlist_pdf_storage_key = storage_key
        self._playlist_pdf_fingerprint = fingerprint

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
    def onboarding_questions(self) -> tuple[OnboardingQuestion, ...]:
        return tuple(self._onboarding_questions)

    @property
    def open_onboarding_questions(self) -> tuple[OnboardingQuestion, ...]:
        return tuple(
            question
            for question in self._onboarding_questions
            if not question.is_answered
        )

    @property
    def unconsumed_user_curation_events(self) -> list[UserCurationEvent]:
        return [event for event in self._user_curation_events if not event.consumed]

    def set_playlist(self, playlist: Playlist) -> Playlist:
        self._assert_track_limit(total_tracks=len(playlist.tracks))
        self._playlist = playlist
        return self._playlist

    def add_tracks(self, tracks: list[PlaylistTrack]) -> Playlist:
        if self._playlist is None:
            self._playlist = Playlist.create(tracks=[])
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
        record_user_curation_event: bool = True,
    ) -> PlaylistTrack:
        if self._playlist is None:
            self._playlist = Playlist.create(tracks=[])
        self._assert_track_limit(total_tracks=len(self._playlist.tracks) + 1)
        track = PlaylistTrack.create(
            title=title,
            artist=artist,
            year=year,
            spotify_uri=spotify_uri,
            cover_url=cover_url,
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
                self._playlist.tracks[index] = track
                return self._playlist
        raise PlaylistTrackNotFoundError(
            f"Track {track_id} not found in playlist {self._playlist.id}."
        )

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

        reference = PlaylistReference.create(
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

        reference = ArtistReference.create(
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

    def add_onboarding_question(
        self,
        *,
        question_text: str,
        hint: str | None = None,
        options: tuple[str, ...] = (),
        recommended_option: str | None = None,
        selection_mode: OnboardingQuestionSelectionMode | str = (
            OnboardingQuestionSelectionMode.SINGLE_SELECT
        ),
        is_last_question: bool = False,
    ) -> OnboardingQuestion:
        sequence_number = len(self._onboarding_questions) + 1
        question = OnboardingQuestion.create(
            sequence_number=sequence_number,
            question_text=question_text,
            hint=hint,
            options=self._with_decide_for_me_option(options),
            recommended_option=recommended_option,
            selection_mode=selection_mode,
            is_last_question=is_last_question,
        )
        self._onboarding_questions.append(question)
        return question

    def answer_onboarding_question(
        self,
        *,
        question_id: UUID,
        answer: str | None = None,
        answers: tuple[str, ...] | list[str] | None = None,
    ) -> OnboardingQuestion:
        normalized_answers = self._normalize_onboarding_answers(
            answer=answer,
            answers=answers,
        )

        for question in self._onboarding_questions:
            if question.id != question_id:
                continue
            self._assert_onboarding_decide_for_me_selection(answers=normalized_answers)
            self._assert_onboarding_answer_count(
                question=question,
                answers=normalized_answers,
            )
            question.answer_with(
                normalized_answers,
                answered_at=datetime.now(UTC),
            )
            return question

        raise ValueError(f"Onboarding question {question_id} not found.")

    def _normalize_onboarding_answers(
        self,
        *,
        answer: str | None,
        answers: tuple[str, ...] | list[str] | None,
    ) -> tuple[str, ...]:
        raw_answers = list(answers or ())
        if answer is not None:
            raw_answers.append(answer)

        normalized: list[str] = []
        seen: set[str] = set()
        for raw_answer in raw_answers:
            value = raw_answer.strip()
            if not value:
                continue
            dedupe_key = value.casefold()
            if dedupe_key in seen:
                # The API accepts both `answer` and `answers`; clients commonly
                # send the same value through both fields. Treat such overlaps as
                # redundant rather than a user-facing duplicate-selection error.
                continue
            seen.add(dedupe_key)
            normalized.append(value)

        if not normalized:
            raise ValueError("Onboarding answer must not be empty.")

        return tuple(normalized)

    def _assert_onboarding_answer_count(
        self,
        *,
        question: OnboardingQuestion,
        answers: tuple[str, ...],
    ) -> None:
        if question.selection_mode == OnboardingQuestionSelectionMode.SINGLE_SELECT:
            if len(answers) != 1:
                raise ValueError(
                    "Single-select onboarding questions require exactly one answer."
                )
            return

        if len(answers) < 1:
            raise ValueError(
                "Multi-select onboarding questions require at least one answer."
            )

    def _assert_onboarding_decide_for_me_selection(
        self,
        *,
        answers: tuple[str, ...],
    ) -> None:
        if DECIDE_FOR_ME_OPTION not in answers:
            return
        if len(answers) != 1:
            raise ValueError(
                'The "Entscheide für mich" option must be selected on its own.'
            )

    def _with_decide_for_me_option(
        self,
        options: tuple[str, ...] | list[str],
    ) -> tuple[str, ...]:
        normalized_options = tuple(options)
        if DECIDE_FOR_ME_OPTION in normalized_options:
            return normalized_options
        return (*normalized_options, DECIDE_FOR_ME_OPTION)

    def _reconstruct_onboarding_history(self) -> None:
        self._remove_onboarding_tool_call_sequences()
        answered = [q for q in self._onboarding_questions if q.is_answered]
        if not answered:
            return
        lines = ["Beantwortete Onboarding-Fragen:"]
        for i, q in enumerate(answered, 1):
            lines.append(f"{i}. {q.question_text} -> {q.answer}")
        self._entries.append(UserMessage.create(content="\n".join(lines)))

    def _remove_onboarding_tool_call_sequences(self) -> None:
        self._entries = [
            entry
            for entry in self._entries
            if not self._is_onboarding_tool_call_sequence(entry)
        ]

    def _is_onboarding_tool_call_sequence(self, entry: SessionEntry) -> bool:
        if not isinstance(entry, ToolCallSequence):
            return False
        if not entry.calls:
            return False
        return all(call.function.is_onboarding_question for call in entry.calls)

    def add_user_message(
        self,
        content: str,
        attachments: list[UserMessageAttachment] | None = None,
        image_attachments: list[ImageAttachment] | None = None,
    ) -> UserMessage:
        if self._find_pending_tool_call_sequence() is not None:
            raise PendingToolCallsError(
                f"Cannot add user message to session {self.id} "
                "while tool calls are pending."
            )
        message = UserMessage.create(
            content=content,
            attachments=attachments,
            image_attachments=image_attachments,
            user_curation_events=self._unbound_unconsumed_user_curation_events(),
        )
        self._entries.append(message)
        return message

    def add_assistant_message(self, content: str = "") -> AssistantMessage:
        message = AssistantMessage.create(content=content)
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

    def add_tool_call(
        self, call: PendingCall, sequence_label: str | None = None
    ) -> ToolCallSequence:
        last = self._entries[-1] if self._entries else None
        if isinstance(last, ToolCallSequence):
            last.add(call)
            return last
        sequence = ToolCallSequence.create(calls=[call], label=sequence_label)
        self._entries.append(sequence)
        return sequence

    def resolve_tool_call(
        self,
        tool_call_id: str,
        result: str,
        items: Sequence[ToolResultItem] = (),
    ) -> CompletedCall:
        sequence = self._require_pending_tool_call_sequence()
        return sequence.resolve(tool_call_id, result, items)

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
        if event.event_type == UserCurationEventType.TRACK_ADDED:
            self.remove_track(event.track_id, record_user_curation_event=False)
            return
        if event.event_type == UserCurationEventType.TRACK_REMOVED:
            self._restore_removed_track(event)
            return

    def _restore_removed_track(self, event: UserCurationEvent) -> PlaylistTrack:
        if self._playlist is None:
            self._playlist = Playlist.create(tracks=[])
        self._assert_track_limit(total_tracks=len(self._playlist.tracks) + 1)
        if event.track_year is None:
            raise UserCurationEventMissingTrackYearError(
                f"User curation event {event.id} cannot restore track "
                f"{event.track_id} because track_year is missing."
            )
        track = PlaylistTrack.restore(
            id=event.track_id,
            created_at=datetime.now(UTC),
            title=event.track_title,
            artist=event.track_artist,
            year=event.track_year,
            spotify_uri=event.track_spotify_uri,
            cover_url=event.track_cover_url,
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
        event = UserCurationEvent.create(
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
        if any(not question.is_answered for question in self._onboarding_questions):
            raise InvalidSessionPhaseTransitionError(
                f"Cannot advance session {self.id} while onboarding questions are unanswered."
            )
        self._reconstruct_onboarding_history()
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
