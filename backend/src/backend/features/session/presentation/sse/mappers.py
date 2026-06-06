from backend.features.session.application import (
    SessionAssistantMessageChunk,
    SessionAssistantMessageCancelled,
    SessionAssistantMessageCompleted,
    SessionAssistantMessageStarted,
    SessionEvent,
    SessionOnboardingQuestionAsked,
    SessionPlaylistSet,
    SessionPlaylistTrackAdded,
    SessionPlaylistTrackRemoved,
    SessionPlaylistTrackReplaced,
    SessionSnapshot,
    SessionSuspendedForInput,
    SessionTitleGenerated,
    SessionToolCallFailed,
    SessionToolCallSequenceAdded,
    SessionToolCallSequenceCompleted,
    SessionToolCallResolved,
)
from backend.features.session.domain import Playlist
from backend.features.session.presentation.mapper import (
    to_entry_response,
    to_playlist_track_response,
    to_tool_call_sequence_response,
)
from backend.features.session.presentation.schemas import (
    AssistantMessageEntryResponse,
)
from backend.features.session.presentation.sse.events import (
    AssistantMessageChunkEvent,
    AssistantMessageCancelledEvent,
    AssistantMessageCompletedEvent,
    AssistantMessageStartedEvent,
    PlaylistPayload,
    PlaylistSetEvent,
    PlaylistTrackAddedEvent,
    PlaylistTrackRemovedEvent,
    PlaylistTrackReplacedEvent,
    OnboardingQuestionAskedEvent,
    ServerEvent,
    SessionSnapshotEvent,
    SessionSnapshotPayload,
    SuspendedForInputEvent,
    TitleGeneratedEvent,
    ToolCallFailedEvent,
    ToolCallSequenceAddedEvent,
    ToolCallSequenceCompletedEvent,
    ToolCallResolvedEvent,
)


def to_server_event(event: SessionEvent) -> ServerEvent:
    if isinstance(event, SessionSnapshot):
        return SessionSnapshotEvent(
            session=SessionSnapshotPayload(
                id=event.session.id,
                title=event.session.title,
                created_at=event.session.created_at,
                entries=[to_entry_response(entry) for entry in event.session.entries],
                playlist=(
                    _to_playlist_payload(event.session.playlist)
                    if event.session.playlist is not None
                    else None
                ),
            )
        )

    if isinstance(event, SessionTitleGenerated):
        return TitleGeneratedEvent(title=event.title)

    if isinstance(event, SessionAssistantMessageStarted):
        return AssistantMessageStartedEvent(
            message_id=event.message.id,
            created_at=event.message.created_at,
        )

    if isinstance(event, SessionAssistantMessageChunk):
        return AssistantMessageChunkEvent(
            message_id=event.message_id,
            chunk=event.chunk,
        )

    if isinstance(event, SessionAssistantMessageCompleted):
        return AssistantMessageCompletedEvent(
            message=AssistantMessageEntryResponse(
                id=event.message.id,
                content=event.message.content,
                created_at=event.message.created_at,
            ),
        )

    if isinstance(event, SessionAssistantMessageCancelled):
        return AssistantMessageCancelledEvent(message_id=event.message_id)

    if isinstance(event, SessionToolCallSequenceAdded):
        return ToolCallSequenceAddedEvent(
            sequence=to_tool_call_sequence_response(event.sequence)
        )

    if isinstance(event, SessionToolCallResolved):
        return ToolCallResolvedEvent(
            sequence_id=event.sequence_id,
            tool_call_id=event.tool_call_id,
            result=event.result,
        )

    if isinstance(event, SessionToolCallFailed):
        return ToolCallFailedEvent(
            sequence_id=event.sequence_id,
            tool_call_id=event.tool_call_id,
            error=event.error,
        )

    if isinstance(event, SessionToolCallSequenceCompleted):
        return ToolCallSequenceCompletedEvent(sequence_id=event.sequence_id)

    if isinstance(event, SessionPlaylistSet):
        return PlaylistSetEvent(playlist=_to_playlist_payload(event.playlist))

    if isinstance(event, SessionPlaylistTrackAdded):
        return PlaylistTrackAddedEvent(
            playlist_id=event.playlist_id,
            track=to_playlist_track_response(event.track),
        )

    if isinstance(event, SessionPlaylistTrackRemoved):
        return PlaylistTrackRemovedEvent(
            playlist_id=event.playlist_id,
            track_id=event.track_id,
        )

    if isinstance(event, SessionPlaylistTrackReplaced):
        return PlaylistTrackReplacedEvent(
            playlist_id=event.playlist_id,
            track_id=event.track_id,
            track=to_playlist_track_response(event.track),
        )

    if isinstance(event, SessionOnboardingQuestionAsked):
        return OnboardingQuestionAskedEvent(
            question=event.question,
            hint=event.hint,
            options=list(event.options),
            selection_mode=event.selection_mode,
            question_id=event.question_id,
            is_last_question=event.is_last_question,
        )

    if isinstance(event, SessionSuspendedForInput):
        return SuspendedForInputEvent(
            kind=event.kind,
            question=event.question,
            hint=event.hint,
            options=list(event.options or []),
            selection_mode=event.selection_mode,
            question_id=event.question_id,
            is_last_question=event.is_last_question,
        )

    raise TypeError(f"Unsupported session event: {type(event).__name__}")


def _to_playlist_payload(playlist: Playlist) -> PlaylistPayload:
    return PlaylistPayload(
        id=playlist.id,
        name=playlist.name,
        tracks=[to_playlist_track_response(track) for track in playlist.tracks],
    )
