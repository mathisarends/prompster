from datetime import UTC, datetime

from agent import (
    AssistantMessageChunkEvent,
    AssistantMessageEvent,
    ContextCompactedEvent,
    DeckUpdatedEvent,
    QuestionAskedEvent,
    SuspendedForUserInputEvent,
    ToolCallEvent,
    ToolCallSequenceStartedEvent,
    ToolResultEvent,
    ToolRetryEvent,
)
from agent.deck import (
    DeckDraft,
    DeckDraftTrack,
    DeckDraftTracksAdded,
    DeckDraftTracksRemoved,
    DeckDraftTracksReplaced,
)
from backend.features.session.application.ports.session_runner import (
    SessionRunnerAssistantMessage,
    SessionRunnerAssistantMessageChunk,
    SessionRunnerContextCompacted,
    SessionRunnerEvent,
    SessionRunnerPlaylistTrackReplacement,
    SessionRunnerPlaylistTracksAdded,
    SessionRunnerPlaylistTracksRemoved,
    SessionRunnerPlaylistTracksReplaced,
    SessionRunnerQuestionAsked,
    SessionRunnerSuspendedForInput,
    SessionRunnerToolCallSequenceStarted,
    SessionRunnerPlaylistUpdated,
    SessionRunnerToolCallCompleted,
    SessionRunnerToolCallRetry,
    SessionRunnerToolCallStarted,
)
from backend.features.session.domain import (
    PendingCall,
    Playlist,
    PlaylistTrack,
    ToolActionType,
    ToolFunction,
    ToolResultItem,
)


class AgentSessionEventMapper:
    """Translates ``agent`` stream events into ``SessionRunner`` events.

    Stateless: a single instance is safe to share. Returns a list so a single
    agent event can fan out to zero or many runner events — and so unknown
    events can be silently dropped without breaking the runner's loop.
    """

    def map(self, event: object) -> list[SessionRunnerEvent]:
        match event:
            case AssistantMessageChunkEvent():
                return [self._map_assistant_chunk(event)]
            case AssistantMessageEvent():
                return [self._map_assistant_message(event)]
            case ToolCallSequenceStartedEvent():
                return [self._map_tool_call_sequence_started(event)]
            case ToolCallEvent():
                return [self._map_tool_call_started(event)]
            case ToolResultEvent():
                return [self._map_tool_call_completed(event)]
            case ToolRetryEvent():
                return [self._map_tool_call_retry(event)]
            case ContextCompactedEvent():
                return [self._map_context_compacted(event)]
            case DeckUpdatedEvent():
                return [self._map_deck_updated(event)]
            case QuestionAskedEvent():
                return [self._map_question_asked(event)]
            case SuspendedForUserInputEvent():
                return [self._map_suspended_for_input(event)]
            case _:
                return []

    def _map_assistant_chunk(
        self, event: AssistantMessageChunkEvent
    ) -> SessionRunnerAssistantMessageChunk:
        return SessionRunnerAssistantMessageChunk(chunk=event.chunk)

    def _map_assistant_message(
        self, event: AssistantMessageEvent
    ) -> SessionRunnerAssistantMessage:
        return SessionRunnerAssistantMessage(content=event.content)

    def _map_tool_call_started(
        self, event: ToolCallEvent
    ) -> SessionRunnerToolCallStarted:
        return SessionRunnerToolCallStarted(
            call=PendingCall(
                id=event.tool_call_id,
                function=ToolFunction(
                    name=event.name,
                    arguments=dict(event.args),
                    status_label=event.status_label,
                    action_type=self._to_tool_action_type(event.action_type),
                    is_onboarding_question=event.is_onboarding_question,
                ),
            )
        )

    def _map_tool_call_sequence_started(
        self, event: ToolCallSequenceStartedEvent
    ) -> SessionRunnerToolCallSequenceStarted:
        return SessionRunnerToolCallSequenceStarted(label=event.label)

    def _map_tool_call_retry(self, event: ToolRetryEvent) -> SessionRunnerToolCallRetry:
        return SessionRunnerToolCallRetry(
            tool_call_id=event.tool_call_id,
            name=event.name,
            attempt=event.attempt,
            max_attempts=event.max_attempts,
            retry_in_seconds=event.retry_in_seconds,
        )

    def _map_tool_call_completed(
        self, event: ToolResultEvent
    ) -> SessionRunnerToolCallCompleted:
        return SessionRunnerToolCallCompleted(
            tool_call_id=event.tool_call_id,
            result=event.result,
            items=[
                ToolResultItem(
                    title=item.title,
                    cover_url=item.cover_url,
                    artist=item.artist,
                    track_uri=item.track_uri,
                )
                for item in event.items
            ],
        )

    def _map_context_compacted(
        self, event: ContextCompactedEvent
    ) -> SessionRunnerContextCompacted:
        return SessionRunnerContextCompacted(
            reason=event.reason,
            tokens_before=event.tokens_before,
            compacted_tool_results=event.compacted_tool_results,
        )

    def _map_deck_updated(self, event: DeckUpdatedEvent) -> SessionRunnerEvent:
        update = event.update
        match update:
            case DeckDraftTracksAdded():
                return SessionRunnerPlaylistTracksAdded(
                    playlist_id=update.deck_draft.id,
                    tracks=[self._to_playlist_track(track) for track in update.tracks],
                )
            case DeckDraftTracksRemoved():
                return SessionRunnerPlaylistTracksRemoved(
                    playlist_id=update.deck_draft.id,
                    track_ids=update.track_ids,
                )
            case DeckDraftTracksReplaced():
                return SessionRunnerPlaylistTracksReplaced(
                    playlist_id=update.deck_draft.id,
                    replacements=[
                        SessionRunnerPlaylistTrackReplacement(
                            track_id=replacement.track_id,
                            track=self._to_playlist_track(replacement.track),
                        )
                        for replacement in update.replacements
                    ],
                )
            case _:
                return SessionRunnerPlaylistUpdated(
                    playlist=self._to_playlist(event.deck_draft)
                )

    def _map_question_asked(
        self, event: QuestionAskedEvent
    ) -> SessionRunnerQuestionAsked:
        return SessionRunnerQuestionAsked(
            question=event.question,
            hint=event.hint,
            options=list(event.options),
            recommended_option=event.recommended_option,
            selection_mode=event.selection_mode,
        )

    def _map_suspended_for_input(
        self, event: SuspendedForUserInputEvent
    ) -> SessionRunnerSuspendedForInput:
        return SessionRunnerSuspendedForInput(
            question=event.question,
            hint=event.hint,
            options=list(event.options),
            recommended_option=event.recommended_option,
            selection_mode=event.selection_mode,
            is_last_question=event.is_last_question,
        )

    def _to_tool_action_type(self, value: str | None) -> ToolActionType | None:
        if value is None:
            return None
        try:
            return ToolActionType(value)
        except ValueError:
            return None

    def _to_playlist(self, deck_draft: DeckDraft) -> Playlist:
        return Playlist.restore(
            id=deck_draft.id,
            created_at=datetime.now(UTC),
            name=deck_draft.name,
            tracks=[self._to_playlist_track(track) for track in deck_draft.tracks],
        )

    def _to_playlist_track(self, track: DeckDraftTrack) -> PlaylistTrack:
        return PlaylistTrack.restore(
            id=track.id,
            created_at=datetime.now(UTC),
            title=track.title,
            artist=track.artist,
            year=track.year,
            spotify_uri=track.spotify_uri,
            cover_url=track.cover_url,
        )
