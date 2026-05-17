from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query, Response, status
from fastapi.responses import StreamingResponse

from backend.features.auth.presentation.dependencies import AuthenticatedUserId
from backend.features.session.application import (
    CreateSessionHandler,
    DeleteSessionHandler,
    GetSessionByIdHandler,
    ListSessionsHandler,
    SearchSpotifyTracksHandler,
    SearchSessionsHandler,
    SendMessageHandler,
    UpdateSessionHandler,
)
from backend.features.session.presentation.dependencies import AuthorizedSession
from backend.features.session.presentation.mapper import (
    to_session_response,
    to_session_summary_response,
    to_spotify_track_response,
)
from backend.features.session.presentation.schemas import (
    ErrorResponse,
    SendMessageRequest,
    SessionCreateRequest,
    SessionResponse,
    SessionSummaryListResponse,
    SessionUpdateRequest,
    SpotifyTrackSearchResponse,
)

router = APIRouter(route_class=DishkaRoute, prefix="/sessions", tags=["sessions"])

_auth_errors = {
    status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
    status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
}
_not_found = {status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}}
_bad_request = {status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse}}


@router.get(
    "",
    response_model=SessionSummaryListResponse,
    status_code=status.HTTP_200_OK,
    operation_id="list_sessions",
    responses=_auth_errors,
)
async def list_sessions(
    authenticated_user_id: AuthenticatedUserId,
    list_handler: FromDishka[ListSessionsHandler],
    search_handler: FromDishka[SearchSessionsHandler],
    q: str | None = Query(default=None, min_length=1, max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> SessionSummaryListResponse:
    if q and q.strip():
        items = await search_handler.handle(
            owner_id=authenticated_user_id,
            query=q,
            limit=limit,
            offset=offset,
        )
    else:
        items = await list_handler.handle(
            owner_id=authenticated_user_id,
            limit=limit,
            offset=offset,
        )

    return SessionSummaryListResponse(
        items=[to_session_summary_response(item) for item in items],
    )


@router.get(
    "/spotify-tracks",
    response_model=SpotifyTrackSearchResponse,
    status_code=status.HTTP_200_OK,
    operation_id="search_spotify_tracks",
    responses=_auth_errors,
)
async def search_spotify_tracks(
    _authenticated_user_id: AuthenticatedUserId,  # keep to ensure authentication
    handler: FromDishka[SearchSpotifyTracksHandler],
    query: str = Query(min_length=1, max_length=200, description="Search query"),
    limit: int = Query(default=20, ge=1, le=50),
) -> SpotifyTrackSearchResponse:
    tracks = await handler.handle(query=query, limit=limit)
    return SpotifyTrackSearchResponse(
        items=[to_spotify_track_response(track) for track in tracks],
    )


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
    operation_id="get_session",
    responses=_auth_errors | _not_found,
)
async def get_session_by_id(
    session: AuthorizedSession,
    handler: FromDishka[GetSessionByIdHandler],
) -> SessionResponse:
    session = await handler.handle(session=session)
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
    handler: FromDishka[CreateSessionHandler],
) -> SessionResponse:
    session = await handler.handle(
        owner_id=authenticated_user_id,
        initial_prompt=body.initial_prompt,
    )
    return to_session_response(session)


@router.post(
    "/{session_id}/messages",
    status_code=status.HTTP_201_CREATED,
    operation_id="send_message",
    responses={
        status.HTTP_201_CREATED: {"content": {"text/plain": {}}},
        **_auth_errors,
        **_bad_request,
        **_not_found,
    },
)
async def send_message(
    session: AuthorizedSession,
    body: SendMessageRequest,
    handler: FromDishka[SendMessageHandler],
) -> StreamingResponse:
    return StreamingResponse(
        handler.stream_response(session=session, content=body.content),
        media_type="text/plain; charset=utf-8",
    )


@router.patch(
    "/{session_id}",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
    operation_id="update_session",
    responses=_auth_errors | _bad_request | _not_found,
)
async def update_session(
    session: AuthorizedSession,
    body: SessionUpdateRequest,
    handler: FromDishka[UpdateSessionHandler],
) -> SessionResponse:
    session = await handler.handle(
        session=session,
        title=body.title,
    )
    return to_session_response(session)


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_session",
    responses=_auth_errors | _not_found,
)
async def delete_session(
    session: AuthorizedSession,
    handler: FromDishka[DeleteSessionHandler],
) -> Response:
    await handler.handle(session=session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
