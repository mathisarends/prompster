from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query, Response, status
from llm import OpenAIModelName
from starlette.responses import StreamingResponse

from backend.features.auth.presentation.dependencies import AuthenticatedUserId
from backend.features.session.application import (
    SessionImageAttachmentReference,
    SessionMessageAttachment,
    SessionConversationService,
    SessionService,
    SessionPlaylistExporter,
    SessionSpotifyPlaylistExporter,
)
from backend.features.session.application.ports import MessageAttachmentStore
from backend.features.session.domain import Session
from backend.features.session.presentation.mapper import (
    to_playlist_track_response,
    to_session_response,
    to_session_summary_response,
    to_spotify_playlist_export_response,
)
from backend.features.session.presentation.schemas import (
    AddPlaylistTrackRequest,
    ErrorResponse,
    ImageAttachmentReferenceRequest,
    PlaylistTrackResponse,
    SendMessageRequest,
    SessionMessageAttachmentRequest,
    SubmitOnboardingAnswerRequest,
    SessionCreateRequest,
    SessionResponse,
    SessionSummaryListResponse,
    SessionUpdateRequest,
    SpotifyPlaylistExportResponse,
)
from backend.features.session.presentation.sse import (
    stream_session_events,
)

router = APIRouter(route_class=DishkaRoute, prefix="/sessions", tags=["sessions"])

_auth_errors = {
    status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
    status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
}
_not_found = {status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}}
_bad_request = {status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse}}
_conflict = {status.HTTP_409_CONFLICT: {"model": ErrorResponse}}
_too_many = {status.HTTP_429_TOO_MANY_REQUESTS: {"model": ErrorResponse}}
_event_stream_response = {
    status.HTTP_200_OK: {
        "description": "Server-sent session events.",
        "content": {"text/event-stream": {"schema": {"type": "string"}}},
    },
}
_pdf_response = {
    status.HTTP_200_OK: {
        "description": "Playlist deck PDF.",
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
    responses=_auth_errors,
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
    responses=_auth_errors | _not_found,
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
    responses=_auth_errors,
)
async def create_session(
    authenticated_user_id: AuthenticatedUserId,
    body: SessionCreateRequest,
    service: FromDishka[SessionService],
    attachment_store: FromDishka[MessageAttachmentStore],
) -> SessionResponse:
    session = await service.create(
        owner_id=authenticated_user_id,
        initial_prompt=body.initial_prompt,
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
    | _auth_errors
    | _bad_request
    | _not_found
    | _too_many,
)
async def send_message(
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    body: SendMessageRequest,
    service: FromDishka[SessionConversationService],
    model_id: OpenAIModelName | None = None,
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
    responses=_auth_errors | _bad_request | _not_found,
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
    responses=_event_stream_response | _auth_errors | _bad_request | _not_found,
)
async def complete_onboarding(
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    service: FromDishka[SessionConversationService],
    model_id: OpenAIModelName | None = None,
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
    responses=_auth_errors | _not_found,
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
    responses=_auth_errors | _not_found,
)
async def add_session_playlist_track(
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    body: AddPlaylistTrackRequest,
    service: FromDishka[SessionService],
) -> PlaylistTrackResponse:
    track = await service.add_playlist_track(
        session_id=session_id,
        user_id=authenticated_user_id,
        title=body.title,
        artist=body.artist,
        year=body.year,
        spotify_uri=body.spotify_uri,
        cover_url=body.cover_url,
    )
    return to_playlist_track_response(track)


@router.delete(
    "/{session_id}/tracks/{track_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="remove_playlist_track",
    responses=_auth_errors | _not_found,
)
async def remove_session_playlist_track(
    session_id: UUID,
    track_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    service: FromDishka[SessionService],
) -> Response:
    await service.remove_playlist_track(
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
    responses=_auth_errors | _not_found | _conflict,
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
    responses=_pdf_response | _auth_errors | _bad_request | _not_found,
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
    response_model=SpotifyPlaylistExportResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="export_session_playlist_to_spotify",
    responses=_auth_errors | _bad_request | _not_found | _conflict,
)
async def export_session_playlist_to_spotify(
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    exporter: FromDishka[SessionSpotifyPlaylistExporter],
) -> SpotifyPlaylistExportResponse:
    exported = await exporter.export(
        session_id=session_id,
        user_id=authenticated_user_id,
    )
    return to_spotify_playlist_export_response(exported)


@router.patch(
    "/{session_id}",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
    operation_id="update_session",
    responses=_auth_errors | _bad_request | _not_found,
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
    responses=_auth_errors | _not_found,
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
    responses=_auth_errors | _not_found,
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
    responses=_auth_errors | _not_found,
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
            expires_in_seconds=900,
        )
    return urls
