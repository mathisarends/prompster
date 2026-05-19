from uuid import UUID

from backend.features.session.application import (
    SessionEvent,
    SessionFollowUpAnswered,
    SessionFollowUpSkipped,
    SessionPlaylistSet,
    SessionPlaylistTrackAdded,
    SessionPlaylistTrackRemoved,
    SessionUserMessageAppended,
)
from backend.features.session.domain import Session
from backend.features.session.presentation.schemas import FollowUpAnswerRequest


def append_user_message(*, session: Session, content: str) -> tuple[SessionEvent, ...]:
    message = session.add_user_message(content=content)
    return (SessionUserMessageAppended(message=message),)


def answer_follow_up(
    *,
    session: Session,
    question_id: UUID,
    answer: FollowUpAnswerRequest,
) -> tuple[SessionEvent, ...]:
    group = session.require_pending_follow_up_group()
    if answer.option_id is not None:
        question = session.answer_follow_up_with_option(
            question_id=question_id,
            option_id=answer.option_id,
        )
    else:
        question = session.answer_follow_up_with_text(
            question_id=question_id,
            text=answer.text or "",
        )
    return (SessionFollowUpAnswered(group_id=group.id, question=question),)


def skip_follow_up(*, session: Session, question_id: UUID) -> tuple[SessionEvent, ...]:
    group = session.require_pending_follow_up_group()
    question = session.skip_follow_up(question_id=question_id)
    return (SessionFollowUpSkipped(group_id=group.id, question_id=question.id),)


def add_playlist_track(
    *,
    session: Session,
    title: str,
    artist: str,
    year: int | None,
    cover_url: str | None,
) -> tuple[SessionEvent, ...]:
    playlist_existed = session.playlist is not None
    track = session.add_track(
        title=title,
        artist=artist,
        year=year,
        cover_url=cover_url,
    )
    playlist = session.playlist
    if playlist is None:
        return ()
    if not playlist_existed:
        return (SessionPlaylistSet(playlist=playlist),)
    return (SessionPlaylistTrackAdded(playlist_id=playlist.id, track=track),)


def remove_playlist_track(
    *,
    session: Session,
    track_id: UUID,
) -> tuple[SessionEvent, ...]:
    playlist = session.playlist
    session.remove_track(track_id=track_id)
    if playlist is None:
        return ()
    return (
        SessionPlaylistTrackRemoved(
            playlist_id=playlist.id,
            track_id=track_id,
        ),
    )
