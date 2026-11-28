from backend.features.session.application import (
    SessionAssistantMessageCancelled,
    SessionAssistantMessageChunk,
    SessionAssistantMessageCompleted,
    SessionAssistantMessageStarted,
    SessionContextCompacted,
    SessionEvent,
    SessionOnboardingQuestionAsked,
    SessionPlaylistSet,
    SessionPlaylistTrackAdded,
    SessionPlaylistTrackRemoved,
    SessionPlaylistTrackReplaced,
    SessionRunStatusChanged,
    SessionSnapshot,
    SessionSuspendedForInput,
    SessionTitleGenerated,
    SessionToolCallFailed,
    SessionToolCallResolved,
    SessionToolCallRetry,
    SessionToolCallSequenceAdded,
    SessionToolCallSequenceCompleted,
)
from backend.features.session.domain import Playlist
from backend.features.session.presentation.mapper import (
    to_entry_response,
    to_playlist_track_response,
    to_tool_call_result_item_response,
    to_tool_call_sequence_response,
)
from backend.features.session.presentation.schemas import (
    AssistantMessageEntryResponse,
)
from backend.features.session.presentation.streams.events import (
    AssistantMessageCancelledEvent,
    AssistantMessageChunkEvent,
    AssistantMessageCompletedEvent,
    AssistantMessageStartedEvent,
    ContextCompactedEvent,
    OnboardingQuestionAskedEvent,
    PlaylistPayload,
    PlaylistSetEvent,
    PlaylistTrackAddedEvent,
    PlaylistTrackRemovedEvent,
    PlaylistTrackReplacedEvent,
    RunStatusChangedEvent,
    SessionSnapshotEvent,
    SessionSnapshotPayload,
    SessionStreamEvent,
    SuspendedForInputEvent,
    TitleGeneratedEvent,
    ToolCallFailedEvent,
    ToolCallResolvedEvent,
    ToolCallRetryEvent,
    ToolCallSequenceAddedEvent,
    ToolCallSequenceCompletedEvent,
)


def to_session_stream_event(event: SessionEvent) -> SessionStreamEvent:
    match event:
        case SessionSnapshot():
            entries = [to_entry_response(entry) for entry in event.session.entries]
            return SessionSnapshotEvent(
                session=SessionSnapshotPayload(
                    id=event.session.id,
                    title=event.session.title,
                    created_at=event.session.created_at,
                    entries=entries,
                    playlist=(
                        _to_playlist_payload(event.session.playlist)
                        if event.session.playlist is not None
                        else None
                    ),
                )
            )

        case SessionTitleGenerated():
            return TitleGeneratedEvent(title=event.title)

        case SessionAssistantMessageStarted():
            return AssistantMessageStartedEvent(
                message_id=event.message.id,
                created_at=event.message.created_at,
            )

        case SessionAssistantMessageChunk():
            return AssistantMessageChunkEvent(
                message_id=event.message_id,
                chunk=event.chunk,
            )

        case SessionAssistantMessageCompleted():
            return AssistantMessageCompletedEvent(
                message=AssistantMessageEntryResponse(
                    id=event.message.id,
                    content=event.message.content,
                    created_at=event.message.created_at,
                ),
            )

        case SessionAssistantMessageCancelled():
            return AssistantMessageCancelledEvent(message_id=event.message_id)

        case SessionToolCallSequenceAdded():
            return ToolCallSequenceAddedEvent(
                sequence=to_tool_call_sequence_response(event.sequence)
            )

        case SessionToolCallResolved():
            result_items = [
                to_tool_call_result_item_response(item) for item in event.items
            ]
            return ToolCallResolvedEvent(
                sequence_id=event.sequence_id,
                tool_call_id=event.tool_call_id,
                result=event.result,
                result_items=result_items,
            )

        case SessionToolCallFailed():
            return ToolCallFailedEvent(
                sequence_id=event.sequence_id,
                tool_call_id=event.tool_call_id,
                error=event.error,
            )

        case SessionToolCallRetry():
            return ToolCallRetryEvent(
                tool_call_id=event.tool_call_id,
                name=event.name,
                attempt=event.attempt,
                max_attempts=event.max_attempts,
                retry_in_seconds=event.retry_in_seconds,
                sequence_id=event.sequence_id,
            )

        case SessionToolCallSequenceCompleted():
            return ToolCallSequenceCompletedEvent(sequence_id=event.sequence_id)

        case SessionContextCompacted():
            return ContextCompactedEvent(
                tokens_before=event.tokens_before,
                tokens_after=event.tokens_after,
            )

        case SessionRunStatusChanged():
            return RunStatusChangedEvent(status=event.status)

        case SessionPlaylistSet():
            return PlaylistSetEvent(playlist=_to_playlist_payload(event.playlist))

        case SessionPlaylistTrackAdded():
            return PlaylistTrackAddedEvent(
                playlist_id=event.playlist_id,
                track=to_playlist_track_response(event.track),
            )

        case SessionPlaylistTrackRemoved():
            return PlaylistTrackRemovedEvent(
                playlist_id=event.playlist_id,
                track_id=event.track_id,
            )

        case SessionPlaylistTrackReplaced():
            return PlaylistTrackReplacedEvent(
                playlist_id=event.playlist_id,
                track_id=event.track_id,
                track=to_playlist_track_response(event.track),
            )

        case SessionOnboardingQuestionAsked():
            return OnboardingQuestionAskedEvent(
                question=event.question,
                hint=event.hint,
                options=list(event.options),
                recommended_option=event.recommended_option,
                selection_mode=event.selection_mode,
                question_id=event.question_id,
                is_last_question=event.is_last_question,
            )

        case SessionSuspendedForInput():
            return SuspendedForInputEvent(
                kind=event.kind,
                question=event.question,
                hint=event.hint,
                options=list(event.options or []),
                recommended_option=event.recommended_option,
                selection_mode=event.selection_mode,
                question_id=event.question_id,
                is_last_question=event.is_last_question,
            )

        case _:
            raise TypeError(f"Unsupported session event: {type(event).__name__}")


def _to_playlist_payload(playlist: Playlist) -> PlaylistPayload:
    tracks = [to_playlist_track_response(track) for track in playlist.tracks]
    return PlaylistPayload(
        id=playlist.id,
        name=playlist.name,
        tracks=tracks,
    )
