from backend.features.session.application import (
    SessionEvent,
    SessionFollowUpAnswered,
    SessionFollowUpSkipped,
    SessionPlaylistSet,
    SessionPlaylistTrackAdded,
    SessionPlaylistTrackRemoved,
    SessionTitleGenerated,
    SessionUserMessageAppended,
)
from backend.features.session.presentation.ws.events import (
    FollowUpAnsweredEvent,
    FollowUpSkippedEvent,
    PlaylistSetEvent,
    PlaylistTrackAddedEvent,
    PlaylistTrackRemovedEvent,
    ServerEvent,
    SessionTitleGeneratedEvent,
    UserMessageAppendedEvent,
)
from backend.features.session.presentation.ws.mapper import (
    to_message_payload,
    to_playlist_payload,
    to_playlist_track_payload,
)


def to_server_event(event: SessionEvent) -> ServerEvent:
    if isinstance(event, SessionTitleGenerated):
        return SessionTitleGeneratedEvent(
            session_id=event.session_id,
            title=event.title,
        )

    if isinstance(event, SessionUserMessageAppended):
        return UserMessageAppendedEvent(message=to_message_payload(event.message))

    if isinstance(event, SessionFollowUpAnswered):
        return FollowUpAnsweredEvent(
            group_id=event.group_id,
            question_id=event.question.id,
            answer_text=event.question.answer_text or "",
            answered_option_id=event.question.answered_option_id,
        )

    if isinstance(event, SessionFollowUpSkipped):
        return FollowUpSkippedEvent(
            group_id=event.group_id,
            question_id=event.question_id,
        )

    if isinstance(event, SessionPlaylistSet):
        return PlaylistSetEvent(playlist=to_playlist_payload(event.playlist))

    if isinstance(event, SessionPlaylistTrackAdded):
        return PlaylistTrackAddedEvent(
            playlist_id=event.playlist_id,
            track=to_playlist_track_payload(event.track),
        )

    if isinstance(event, SessionPlaylistTrackRemoved):
        return PlaylistTrackRemovedEvent(
            playlist_id=event.playlist_id,
            track_id=event.track_id,
        )

    raise TypeError(f"Unsupported session event: {type(event).__name__}")
