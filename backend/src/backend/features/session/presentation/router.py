from uuid import UUID

from backend.features.auth.presentation.dependencies import AuthenticatedUserId
from backend.features.auth.presentation.exception_handlers import (
    AUTHENTICATION_REQUIRED_ERROR,
)
from backend.features.session.application import (
    SessionConversationService,
    SessionImageAttachmentReference,
    SessionMessageAttachment,
    SessionPlaylistExporter,
    SessionService,
    SessionSpotifyPlaylistExporter,
)
from backend.features.session.application.ports import MessageAttachmentStore
from backend.features.session.domain import Session
from backend.features.session.presentation.exception_handlers import (
    INVALID_SESSION_PHASE_TRANSITION_ERROR,
    INVALID_SPOTIFY_TRACK_URI_ERROR,
    PLAYLIST_TRACK_LIMIT_EXCEEDED_ERROR,
    PLAYLIST_TRACK_NOT_FOUND_ERROR,
    SESSION_ACCESS_DENIED_ERROR,
    SESSION_ERRORS,
    SESSION_EXPORT_REQUIRES_SPOTIFY_CONNECTION_ERROR,
    SESSION_NOT_FOUND_ERROR,
    SESSION_PLAYLIST_EMPTY_ERROR,
    SESSION_PLAYLIST_MISSING_SPOTIFY_TRACKS_ERROR,
    SPOTIFY_TRACK_NOT_FOUND_ERROR,
    SPOTIFY_TRACK_YEAR_MISSING_ERROR,
    USER_CURATION_EVENT_ALREADY_CONSUMED_ERROR,
    USER_CURATION_EVENT_MISSING_TRACK_YEAR_ERROR,
    USER_CURATION_EVENT_NOT_FOUND_ERROR,
    InvalidSpotifyTrackUriError,
    SpotifyTrackNotFoundError,
    SpotifyTrackYearMissingError,
)
from backend.features.session.presentation.mapper import (
    to_playlist_track_response,
    to_session_response,
    to_session_summary_response,
)
from backend.features.session.presentation.schemas import (
    AddPlaylistTrackRequest,
    AddSpotifyPlaylistTrackRequest,
    ImageAttachmentReferenceRequest,
    PlaylistTrackResponse,
    SendMessageRequest,
    SessionCreateRequest,
    SessionMessageAttachmentRequest,
    SessionResponse,
    SessionSummaryListResponse,
    SessionUpdateRequest,
    SubmitOnboardingAnswerRequest,
)
from backend.features.session.presentation.sse import (
    stream_session_events,
    stream_spotify_export,
)
from backend.features.spotify.application.ports import SpotifySearch
from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query, Response, status
from llm import ModelId
from starlette.responses import StreamingResponse

router = APIRouter(route_class=DishkaRoute, prefix="/sessions", tags=["sessions"])

_SESSION_IMAGE_ATTACHMENT_URL_TTL_SECONDS = 60 * 60 * 24
_event_stream_response = {
    status.HTTP_200_OK: {
        "description": "Server-sent session events.",
        "x-fastapi-canon-errors": [],
        "content": {"text/event-stream": {"schema": {"type": "string"}}},
    },
}
_pdf_response = {
    status.HTTP_200_OK: {
        "description": "Playlist deck PDF.",
        "x-fastapi-canon-errors": [],
        "content": {
            "application/pdf": {"schema": {"type": "string", "format": "binary"}}
        },
    }
}


@router.get(
    "",
    response_model=SessionSummaryListResponse,
    status_code=status.HTTP_200_OK,
    operation_id="list_sessions",
    responses=SESSION_ERRORS.responses(AUTHENTICATION_REQUIRED_ERROR),
)
async def list_sessions(
    authenticated_user_id: AuthenticatedUserId,
    service: FromDishka[SessionService],
    q: str | None = Query(default=None, min_length=1, max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> SessionSummaryListResponse:
    if q and q.strip():
        items = await service.search(
            owner_id=authenticated_user_id,
            query=q,
            limit=limit,
            offset=offset,
        )
    else:
        items = await service.list(
            owner_id=authenticated_user_id,
            limit=limit,
            offset=offset,
        )

    return SessionSummaryListResponse(
        items=[to_session_summary_response(item) for item in items],
    )


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
    operation_id="get_session",
    responses=SESSION_ERRORS.responses(
        AUTHENTICATION_REQUIRED_ERROR,
        SESSION_NOT_FOUND_ERROR,
        SESSION_ACCESS_DENIED_ERROR,
    ),
)
async def get_session_by_id(
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    service: FromDishka[SessionService],
    attachment_store: FromDishka[MessageAttachmentStore],
) -> SessionResponse:
    session = await service.get_by_id(
        session_id=session_id,
        user_id=authenticated_user_id,
    )
    return await _to_session_response_with_signed_urls(
        session=session,
        attachment_store=attachment_store,
    )


@router.post(
    "",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_session",
    responses=SESSION_ERRORS.responses(AUTHENTICATION_REQUIRED_ERROR),
)
async def create_session(
    authenticated_user_id: AuthenticatedUserId,
    body: SessionCreateRequest,
    service: FromDishka[SessionService],
    attachment_store: FromDishka[MessageAttachmentStore],
) -> SessionResponse:
    session = await service.create(
        owner_id=authenticated_user_id,
    )
    return await _to_session_response_with_signed_urls(
        session=session,
        attachment_store=attachment_store,
    )


@router.post(
    "/{session_id}/messages",
    response_class=StreamingResponse,
    status_code=status.HTTP_200_OK,
    operation_id="send_message",
    responses=_event_stream_response
    | SESSION_ERRORS.responses(
        AUTHENTICATION_REQUIRED_ERROR,
    ),
)
async def send_message(
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    body: SendMessageRequest,
    service: FromDishka[SessionConversationService],
    model_id: ModelId | None = None,
) -> StreamingResponse:
    return stream_session_events(
        service.send_message(
            session_id=session_id,
            user_id=authenticated_user_id,
            content=body.content,
            model_id=model_id,
            attachments=_to_session_message_attachments(body.attachments),
            image_attachments=_to_session_image_attachment_references(
                body.image_attachments,
            ),
        )
    )


@router.post(
    "/{session_id}/onboarding-answer",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
    operation_id="submit_onboarding_answer",
    responses=SESSION_ERRORS.responses(
        AUTHENTICATION_REQUIRED_ERROR,
        SESSION_NOT_FOUND_ERROR,
        SESSION_ACCESS_DENIED_ERROR,
        INVALID_SESSION_PHASE_TRANSITION_ERROR,
    ),
)
async def submit_onboarding_answer(
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    body: SubmitOnboardingAnswerRequest,
    service: FromDishka[SessionConversationService],
    attachment_store: FromDishka[MessageAttachmentStore],
) -> SessionResponse:
    session = await service.submit_onboarding_answer(
        session_id=session_id,
        user_id=authenticated_user_id,
        question_id=body.question_id,
        answer=body.answer,
        answers=body.answers,
    )
    return await _to_session_response_with_signed_urls(
        session=session,
        attachment_store=attachment_store,
    )


@router.post(
    "/{session_id}/onboarding/complete",
    response_class=StreamingResponse,
    status_code=status.HTTP_200_OK,
    operation_id="complete_onboarding",
    responses=_event_stream_response
    | SESSION_ERRORS.responses(
        AUTHENTICATION_REQUIRED_ERROR,
    ),
)
async def complete_onboarding(
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    service: FromDishka[SessionConversationService],
    model_id: ModelId | None = None,
) -> StreamingResponse:
    return stream_session_events(
        service.complete_onboarding(
            session_id=session_id,
            user_id=authenticated_user_id,
            model_id=model_id,
        )
    )


@router.post(
    "/{session_id}/messages/stop",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="stop_message",
    responses=SESSION_ERRORS.responses(
        AUTHENTICATION_REQUIRED_ERROR,
        SESSION_NOT_FOUND_ERROR,
        SESSION_ACCESS_DENIED_ERROR,
    ),
)
async def stop_message(
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    service: FromDishka[SessionConversationService],
) -> Response:
    await service.stop_message(
        session_id=session_id,
        user_id=authenticated_user_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{session_id}/tracks",
    response_model=PlaylistTrackResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="add_playlist_track",
    responses=SESSION_ERRORS.responses(
        AUTHENTICATION_REQUIRED_ERROR,
        SESSION_NOT_FOUND_ERROR,
        SESSION_ACCESS_DENIED_ERROR,
        PLAYLIST_TRACK_LIMIT_EXCEEDED_ERROR,
    ),
)
async def add_session_playlist_track(
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    body: AddPlaylistTrackRequest,
    service: FromDishka[SessionService],
) -> PlaylistTrackResponse:
    track = await service.add_track(
        session_id=session_id,
        user_id=authenticated_user_id,
        title=body.title,
        artist=body.artist,
        year=body.year,
        spotify_uri=body.spotify_uri,
        cover_url=body.cover_url,
    )
    return to_playlist_track_response(track)


@router.post(
    "/{session_id}/tracks/spotify",
    response_model=PlaylistTrackResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="add_spotify_playlist_track",
    responses=SESSION_ERRORS.responses(
        AUTHENTICATION_REQUIRED_ERROR,
        SESSION_NOT_FOUND_ERROR,
        SESSION_ACCESS_DENIED_ERROR,
        PLAYLIST_TRACK_LIMIT_EXCEEDED_ERROR,
        INVALID_SPOTIFY_TRACK_URI_ERROR,
        SPOTIFY_TRACK_NOT_FOUND_ERROR,
        SPOTIFY_TRACK_YEAR_MISSING_ERROR,
    ),
)
async def add_session_spotify_playlist_track(
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    body: AddSpotifyPlaylistTrackRequest,
    service: FromDishka[SessionService],
    spotify_search: FromDishka[SpotifySearch],
) -> PlaylistTrackResponse:
    spotify_track_id = _spotify_track_id_from_uri(body.spotify_uri)
    if spotify_track_id is None:
        raise InvalidSpotifyTrackUriError

    spotify_track = await spotify_search.get_track(track_id=spotify_track_id)
    if spotify_track is None:
        raise SpotifyTrackNotFoundError
    if spotify_track.year is None:
        raise SpotifyTrackYearMissingError

    track = await service.add_track(
        session_id=session_id,
        user_id=authenticated_user_id,
        title=spotify_track.title,
        artist=spotify_track.artist,
        year=spotify_track.year,
        spotify_uri=f"spotify:track:{spotify_track.id}",
        cover_url=spotify_track.cover_url,
    )
    return to_playlist_track_response(track)


@router.delete(
    "/{session_id}/tracks/{track_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="remove_playlist_track",
    responses=SESSION_ERRORS.responses(
        AUTHENTICATION_REQUIRED_ERROR,
        SESSION_NOT_FOUND_ERROR,
        SESSION_ACCESS_DENIED_ERROR,
        PLAYLIST_TRACK_NOT_FOUND_ERROR,
    ),
)
async def remove_session_playlist_track(
    session_id: UUID,
    track_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    service: FromDishka[SessionService],
) -> Response:
    await service.remove_track(
        session_id=session_id,
        user_id=authenticated_user_id,
        track_id=track_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{session_id}/curation-events/{event_id}/restore",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
    operation_id="restore_user_curation_event",
    responses=SESSION_ERRORS.responses(
        AUTHENTICATION_REQUIRED_ERROR,
        SESSION_NOT_FOUND_ERROR,
        SESSION_ACCESS_DENIED_ERROR,
        USER_CURATION_EVENT_NOT_FOUND_ERROR,
        USER_CURATION_EVENT_ALREADY_CONSUMED_ERROR,
        USER_CURATION_EVENT_MISSING_TRACK_YEAR_ERROR,
    ),
)
async def restore_session_user_curation_event(
    session_id: UUID,
    event_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    service: FromDishka[SessionService],
    attachment_store: FromDishka[MessageAttachmentStore],
) -> SessionResponse:
    session = await service.restore_user_curation_event(
        session_id=session_id,
        user_id=authenticated_user_id,
        event_id=event_id,
    )
    return await _to_session_response_with_signed_urls(
        session=session,
        attachment_store=attachment_store,
    )


@router.get(
    "/{session_id}/playlist/pdf",
    status_code=status.HTTP_200_OK,
    operation_id="export_session_playlist",
    responses=_pdf_response
    | SESSION_ERRORS.responses(
        AUTHENTICATION_REQUIRED_ERROR,
        SESSION_NOT_FOUND_ERROR,
        SESSION_ACCESS_DENIED_ERROR,
        SESSION_PLAYLIST_EMPTY_ERROR,
    ),
)
async def export_session_playlist(
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    exporter: FromDishka[SessionPlaylistExporter],
    pages: int | None = Query(default=None, ge=1, le=100),
) -> Response:
    pdf = await exporter.export(
        session_id=session_id,
        user_id=authenticated_user_id,
        page_limit=pages,
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="session-{session_id}.pdf"'
        },
    )


@router.post(
    "/{session_id}/playlist/spotify",
    response_class=StreamingResponse,
    status_code=status.HTTP_200_OK,
    operation_id="export_session_playlist_to_spotify",
    responses=_event_stream_response
    | SESSION_ERRORS.responses(
        AUTHENTICATION_REQUIRED_ERROR,
        SESSION_NOT_FOUND_ERROR,
        SESSION_ACCESS_DENIED_ERROR,
        SESSION_PLAYLIST_EMPTY_ERROR,
        SESSION_PLAYLIST_MISSING_SPOTIFY_TRACKS_ERROR,
        SESSION_EXPORT_REQUIRES_SPOTIFY_CONNECTION_ERROR,
    ),
)
async def export_session_playlist_to_spotify(
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    exporter: FromDishka[SessionSpotifyPlaylistExporter],
) -> StreamingResponse:
    # Validate up front so domain errors (empty playlist, no Spotify connection,
    # …) surface as HTTP responses; the stream then carries only the Spotify
    # writes, whose retries are emitted live before the terminal result.
    plan = await exporter.prepare(
        session_id=session_id,
        user_id=authenticated_user_id,
    )
    return stream_spotify_export(exporter, plan)


@router.patch(
    "/{session_id}",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
    operation_id="update_session",
    responses=SESSION_ERRORS.responses(
        AUTHENTICATION_REQUIRED_ERROR,
        SESSION_NOT_FOUND_ERROR,
        SESSION_ACCESS_DENIED_ERROR,
    ),
)
async def update_session(
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    body: SessionUpdateRequest,
    service: FromDishka[SessionService],
    attachment_store: FromDishka[MessageAttachmentStore],
) -> SessionResponse:
    session = await service.update(
        session_id=session_id,
        user_id=authenticated_user_id,
        title=body.title,
    )
    return await _to_session_response_with_signed_urls(
        session=session,
        attachment_store=attachment_store,
    )


@router.post(
    "/{session_id}/star",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
    operation_id="star_session",
    responses=SESSION_ERRORS.responses(
        AUTHENTICATION_REQUIRED_ERROR,
        SESSION_NOT_FOUND_ERROR,
        SESSION_ACCESS_DENIED_ERROR,
    ),
)
async def star_session(
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    service: FromDishka[SessionService],
    attachment_store: FromDishka[MessageAttachmentStore],
) -> SessionResponse:
    session = await service.star(
        session_id=session_id,
        user_id=authenticated_user_id,
    )
    return await _to_session_response_with_signed_urls(
        session=session,
        attachment_store=attachment_store,
    )


@router.post(
    "/{session_id}/unstar",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
    operation_id="unstar_session",
    responses=SESSION_ERRORS.responses(
        AUTHENTICATION_REQUIRED_ERROR,
        SESSION_NOT_FOUND_ERROR,
        SESSION_ACCESS_DENIED_ERROR,
    ),
)
async def unstar_session(
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    service: FromDishka[SessionService],
    attachment_store: FromDishka[MessageAttachmentStore],
) -> SessionResponse:
    session = await service.unstar(
        session_id=session_id,
        user_id=authenticated_user_id,
    )
    return await _to_session_response_with_signed_urls(
        session=session,
        attachment_store=attachment_store,
    )


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_session",
    responses=SESSION_ERRORS.responses(
        AUTHENTICATION_REQUIRED_ERROR,
        SESSION_NOT_FOUND_ERROR,
        SESSION_ACCESS_DENIED_ERROR,
    ),
)
async def delete_session(
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    service: FromDishka[SessionService],
) -> Response:
    await service.delete(session_id=session_id, user_id=authenticated_user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def _to_session_response_with_signed_urls(
    *,
    session: Session,
    attachment_store: MessageAttachmentStore,
) -> SessionResponse:
    image_urls_by_storage_key = await _build_image_urls_by_storage_key(
        session=session,
        attachment_store=attachment_store,
    )
    return to_session_response(
        session,
        image_urls_by_storage_key=image_urls_by_storage_key,
    )


def _to_session_message_attachments(
    attachments: list[SessionMessageAttachmentRequest],
) -> list[SessionMessageAttachment]:
    return [
        SessionMessageAttachment(
            kind=attachment.kind,
            external_id=attachment.external_id,
            title=attachment.title,
            subtitle=attachment.subtitle,
            image_url=attachment.image_url,
            spotify_id=attachment.spotify_id,
        )
        for attachment in attachments
    ]


def _to_session_image_attachment_references(
    attachments: list[ImageAttachmentReferenceRequest],
) -> list[SessionImageAttachmentReference]:
    return [
        SessionImageAttachmentReference(
            id=attachment.id,
            storage_key=attachment.storage_key,
            content_type=attachment.content_type,
            file_name=attachment.file_name,
            size_bytes=attachment.size_bytes,
        )
        for attachment in attachments
    ]


async def _build_image_urls_by_storage_key(
    *,
    session: Session,
    attachment_store: MessageAttachmentStore,
) -> dict[str, str]:
    storage_keys: set[str] = set()
    for entry in session.entries:
        image_attachments = getattr(entry, "image_attachments", ())
        for attachment in image_attachments:
            storage_keys.add(attachment.storage_key)

    urls: dict[str, str] = {}
    for storage_key in storage_keys:
        urls[storage_key] = await attachment_store.create_signed_url(
            storage_key=storage_key,
            expires_in_seconds=_SESSION_IMAGE_ATTACHMENT_URL_TTL_SECONDS,
        )
    return urls


def _spotify_track_id_from_uri(value: str) -> str | None:
    normalized = value.strip()
    if not normalized:
        return None

    if normalized.startswith("spotify:track:"):
        track_id = normalized.rsplit(":", maxsplit=1)[-1]
        return track_id or None

    marker = "/track/"
    if marker in normalized:
        track_id = normalized.split(marker, maxsplit=1)[1]
        track_id = track_id.split("?", maxsplit=1)[0].split("/", maxsplit=1)[0]
        return track_id or None

    if "/" not in normalized and ":" not in normalized:
        return normalized

    return None
