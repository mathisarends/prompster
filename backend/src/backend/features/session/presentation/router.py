from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query, Response, status
from starlette.responses import StreamingResponse

from backend.features.auth.presentation.dependencies import AuthenticatedUserId
from backend.features.session.application import (
    FollowUpAnswer,
    SessionConversationService,
    SessionService,
    SessionPlaylistExporter,
    SessionSpotifyPlaylistExporter,
)
from backend.features.session.presentation.mapper import (
    to_playlist_track_response,
    to_session_response,
    to_session_summary_response,
    to_spotify_playlist_export_response,
)
from backend.features.session.presentation.schemas import (
    AddPlaylistTrackRequest,
    ErrorResponse,
    FollowUpAction,
    FollowUpRequest,
    PlaylistTrackResponse,
    SendMessageRequest,
    SessionCreateRequest,
    SessionResponse,
    SessionSummaryListResponse,
    SessionUpdateRequest,
    SpotifyPlaylistExportResponse,
)
from backend.features.session.presentation.sse import (
    SessionEventSchema,
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
    "/events/schema",
    response_model=SessionEventSchema,
    status_code=status.HTTP_200_OK,
    operation_id="get_session_event_schema",
    responses=_auth_errors,
)
async def get_session_event_schema(
    _authenticated_user_id: AuthenticatedUserId,
) -> SessionEventSchema:
    return SessionEventSchema()


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
) -> SessionResponse:
    session = await service.get_by_id(
        session_id=session_id,
        user_id=authenticated_user_id,
    )
    return to_session_response(session)


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
) -> SessionResponse:
    session = await service.create(
        owner_id=authenticated_user_id,
        initial_prompt=body.initial_prompt,
    )
    return to_session_response(session)


@router.post(
    "/{session_id}/messages",
    status_code=status.HTTP_200_OK,
    operation_id="send_message",
    responses=_event_stream_response | _auth_errors | _bad_request | _not_found,
)
async def send_message(
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    body: SendMessageRequest,
    service: FromDishka[SessionConversationService],
) -> StreamingResponse:
    return stream_session_events(
        service.send_message(
            session_id=session_id,
            user_id=authenticated_user_id,
            content=body.content,
        )
    )


@router.post(
    "/{session_id}/follow-ups",
    status_code=status.HTTP_200_OK,
    operation_id="handle_follow_up",
    responses=_event_stream_response | _auth_errors | _bad_request | _not_found,
)
async def handle_follow_up(
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    body: FollowUpRequest,
    service: FromDishka[SessionConversationService],
) -> StreamingResponse:
    if body.action == FollowUpAction.ANSWER:
        return stream_session_events(
            service.answer_follow_ups(
                session_id=session_id,
                user_id=authenticated_user_id,
                answers=[
                    FollowUpAnswer(
                        question_id=a.question_id,
                        option_id=a.option_id,
                        text=a.text,
                    )
                    for a in body.answers
                ],
            )
        )

    return stream_session_events(
        service.skip_remaining_follow_ups(
            session_id=session_id, user_id=authenticated_user_id
        )
    )


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
        is_pinned=body.is_pinned,
    )
    return to_playlist_track_response(track)


@router.post(
    "/{session_id}/tracks/{track_id}/pin",
    response_model=PlaylistTrackResponse,
    status_code=status.HTTP_200_OK,
    operation_id="pin_playlist_track",
    responses=_auth_errors | _not_found,
)
async def pin_session_playlist_track(
    session_id: UUID,
    track_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    service: FromDishka[SessionService],
) -> PlaylistTrackResponse:
    track = await service.pin_playlist_track(
        session_id=session_id,
        user_id=authenticated_user_id,
        track_id=track_id,
    )
    return to_playlist_track_response(track)


@router.post(
    "/{session_id}/tracks/{track_id}/unpin",
    response_model=PlaylistTrackResponse,
    status_code=status.HTTP_200_OK,
    operation_id="unpin_playlist_track",
    responses=_auth_errors | _not_found,
)
async def unpin_session_playlist_track(
    session_id: UUID,
    track_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    service: FromDishka[SessionService],
) -> PlaylistTrackResponse:
    track = await service.unpin_playlist_track(
        session_id=session_id,
        user_id=authenticated_user_id,
        track_id=track_id,
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
) -> SessionResponse:
    session = await service.update(
        session_id=session_id,
        user_id=authenticated_user_id,
        title=body.title,
    )
    return to_session_response(session)


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
) -> SessionResponse:
    session = await service.star(
        session_id=session_id,
        user_id=authenticated_user_id,
    )
    return to_session_response(session)


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
) -> SessionResponse:
    session = await service.unstar(
        session_id=session_id,
        user_id=authenticated_user_id,
    )
    return to_session_response(session)


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
