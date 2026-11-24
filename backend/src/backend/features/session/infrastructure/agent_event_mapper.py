from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from agent import (
    AgentEvent,
    AssistantRepliedEvent,
    Deck,
    DeckCreatedEvent,
    DeckTrack,
    DeckTracksAddedEvent,
    DeckTracksRemovedEvent,
    DeckTracksReplacedEvent,
    PlaylistsFoundEvent,
    QuestionAskedEvent,
    SpotifyRetryEvent,
    ToolCallAnnouncedEvent,
    TracksFoundEvent,
)
from harnessed import SessionStatus
from harnessed.events import (
    CompactionFinishedEvent,
    CompactionStartedEvent,
    SessionStatusChangedEvent,
    TextDeltaEvent,
    ToolCallFinishedEvent,
)
from harnessed.events.completion import TurnResultEvent
from harnessed.models import StopReason

from backend.features.session.application.ports import (
    SessionRunnerAssistantMessage,
    SessionRunnerAssistantMessageChunk,
    SessionRunnerCancelled,
    SessionRunnerContextCompacted,
    SessionRunnerEvent,
    SessionRunnerPlaylistTrackReplacement,
    SessionRunnerPlaylistTracksAdded,
    SessionRunnerPlaylistTracksRemoved,
    SessionRunnerPlaylistTracksReplaced,
    SessionRunnerPlaylistUpdated,
    SessionRunnerQuestionAsked,
    SessionRunnerRunStatusChanged,
    SessionRunnerSuspendedForInput,
    SessionRunnerToolCallCompleted,
    SessionRunnerToolCallRetry,
    SessionRunnerToolCallSequenceStarted,
    SessionRunnerToolCallStarted,
)
from backend.features.session.domain import (
    PendingCall,
    Playlist,
    PlaylistTrack,
    RunStatus,
    ToolActionType,
    ToolFunction,
    ToolResultItem,
)


class AgentRunEventMapper:
    """Translates one run's agent events into ``SessionRunner`` events.

    Create one per run: it collects result previews until their tool call
    finishes, remembers which calls the UI shows, and tracks the run status.
    """

    def __init__(self) -> None:
        self._announced: set[str] = set()
        self._previews: dict[str, list[ToolResultItem]] = {}
        self._status = RunStatus.RUNNING

    def map(self, event: AgentEvent) -> list[SessionRunnerEvent]:
        match event:
            case TextDeltaEvent(text=text) if text:
                return [SessionRunnerAssistantMessageChunk(chunk=text)]
            case AssistantRepliedEvent():
                return [SessionRunnerAssistantMessage(content=event.text)]
            case ToolCallAnnouncedEvent():
                return self._announce(event)
            case ToolCallFinishedEvent():
                return self._finish(event)
            case TracksFoundEvent() | PlaylistsFoundEvent():
                self._previews[event.call_id] = _previews(event)
                return []
            case SpotifyRetryEvent():
                return [_retry(event)]
            case DeckCreatedEvent():
                return [SessionRunnerPlaylistUpdated(playlist=_playlist(event.deck))]
            case (
                DeckTracksAddedEvent()
                | DeckTracksRemovedEvent()
                | DeckTracksReplacedEvent()
            ):
                return [_playlist_change(event)]
            case QuestionAskedEvent():
                return [_question(event)]
            case CompactionStartedEvent():
                return self._compaction_started()
            case CompactionFinishedEvent():
                return self._compaction_finished(event)
            case SessionStatusChangedEvent():
                return self._status_changed(event.status)
            case TurnResultEvent():
                return _turn_ended(event)
        return []

    def _announce(self, event: ToolCallAnnouncedEvent) -> list[SessionRunnerEvent]:
        call = event.call
        self._announced.add(call.id)
        action_type = (
            ToolActionType(event.action_type.value) if event.action_type else None
        )
        return [
            SessionRunnerToolCallSequenceStarted(label=event.batch_label),
            SessionRunnerToolCallStarted(
                call=PendingCall(
                    id=call.id,
                    function=ToolFunction(
                        name=call.name,
                        arguments=_plain_json(call.arguments),
                        status_label=event.status_label,
                        action_type=action_type,
                    ),
                )
            ),
        ]

    def _finish(self, event: ToolCallFinishedEvent) -> list[SessionRunnerEvent]:
        call_id = event.call.id
        items = self._previews.pop(call_id, [])
        # Calls the UI never showed, such as onboarding questions, end silently.
        if call_id not in self._announced:
            return []
        self._announced.discard(call_id)
        return [
            SessionRunnerToolCallCompleted(
                tool_call_id=call_id, result=event.result.text, items=items
            )
        ]

    def _compaction_started(self) -> list[SessionRunnerEvent]:
        return self._set_status(RunStatus.COMPACTING)

    def _compaction_finished(
        self, event: CompactionFinishedEvent
    ) -> list[SessionRunnerEvent]:
        events: list[SessionRunnerEvent] = []
        if event.after_tokens is not None:
            events.append(
                SessionRunnerContextCompacted(
                    tokens_before=event.before_tokens, tokens_after=event.after_tokens
                )
            )
        return [*events, *self._set_status(RunStatus.RUNNING)]

    def _status_changed(self, status: SessionStatus) -> list[SessionRunnerEvent]:
        match status:
            case SessionStatus.PAUSED:
                return self._set_status(RunStatus.PAUSED)
            case SessionStatus.RUNNING:
                return self._set_status(RunStatus.RUNNING)
        return []

    def _set_status(self, status: RunStatus) -> list[SessionRunnerEvent]:
        if status is self._status:
            return []
        self._status = status
        return [SessionRunnerRunStatusChanged(status=status)]


def _turn_ended(event: TurnResultEvent[Any]) -> list[SessionRunnerEvent]:
    if event.result.stop_reason in (StopReason.ABORTED, StopReason.STOPPED):
        return [SessionRunnerCancelled()]
    return []


def _previews(event: TracksFoundEvent | PlaylistsFoundEvent) -> list[ToolResultItem]:
    if isinstance(event, TracksFoundEvent):
        items = [
            ToolResultItem(
                title=track.title,
                cover_url=track.cover_url,
                artist=track.artist,
                track_uri=track.uri,
            )
            for track in event.tracks
        ]
    else:
        items = [
            ToolResultItem(title=playlist.name, cover_url=playlist.cover_url)
            for playlist in event.playlists
        ]
    return items[:_PREVIEW_LIMIT]


def _retry(event: SpotifyRetryEvent) -> SessionRunnerToolCallRetry:
    return SessionRunnerToolCallRetry(
        tool_call_id=event.call_id,
        name=event.tool_name,
        attempt=event.attempt,
        max_attempts=event.max_attempts,
        retry_in_seconds=event.retry_in_seconds,
    )


def _question(event: QuestionAskedEvent) -> SessionRunnerEvent:
    if event.is_last_question:
        return SessionRunnerSuspendedForInput(
            question=event.question,
            hint=event.hint,
            options=list(event.options),
            recommended_option=event.recommended_option,
            selection_mode=event.selection_mode,
            is_last_question=True,
        )
    return SessionRunnerQuestionAsked(
        question=event.question,
        hint=event.hint,
        options=list(event.options),
        recommended_option=event.recommended_option,
        selection_mode=event.selection_mode,
    )


def _playlist_change(
    event: DeckTracksAddedEvent | DeckTracksRemovedEvent | DeckTracksReplacedEvent,
) -> SessionRunnerEvent:
    playlist_id = UUID(event.deck_id)
    match event:
        case DeckTracksAddedEvent():
            tracks = [_playlist_track(track) for track in event.tracks]
            return SessionRunnerPlaylistTracksAdded(
                playlist_id=playlist_id, tracks=tracks
            )
        case DeckTracksRemovedEvent():
            track_ids = [UUID(track_id) for track_id in event.track_ids]
            return SessionRunnerPlaylistTracksRemoved(
                playlist_id=playlist_id, track_ids=track_ids
            )
        case DeckTracksReplacedEvent():
            replacements = [
                SessionRunnerPlaylistTrackReplacement(
                    track_id=UUID(replacement.track_id),
                    track=_playlist_track(replacement.track),
                )
                for replacement in event.replacements
            ]
            return SessionRunnerPlaylistTracksReplaced(
                playlist_id=playlist_id, replacements=replacements
            )


def _playlist(deck: Deck) -> Playlist:
    tracks = [_playlist_track(track) for track in deck.tracks]
    return Playlist.restore(
        id=UUID(deck.id), created_at=datetime.now(UTC), name=deck.name, tracks=tracks
    )


def _playlist_track(track: DeckTrack) -> PlaylistTrack:
    return PlaylistTrack.restore(
        id=UUID(track.id),
        created_at=datetime.now(UTC),
        title=track.title,
        artist=track.artist,
        year=track.year,
        spotify_uri=track.spotify_uri,
        cover_url=track.cover_url,
    )


def _plain_json(value: Any) -> Any:
    """Copy harnessed's frozen tool arguments into plain JSON containers."""
    if isinstance(value, Mapping):
        return {key: _plain_json(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_plain_json(item) for item in value]
    return value


# Enough results to show what a tool found, without persisting unbounded lists.
_PREVIEW_LIMIT = 10
