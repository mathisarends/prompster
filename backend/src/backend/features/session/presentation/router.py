from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query, Response, status

from backend.features.auth.presentation.dependencies import AuthenticatedUserId
from backend.features.session.application import (
    SearchSpotifyTracksHandler,
    SessionService,
)
from backend.features.session.presentation.mapper import (
    to_session_response,
    to_session_summary_response,
    to_spotify_track_response,
)
from backend.features.session.presentation.schemas import (
    ErrorResponse,
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
    result = await service.create(
        owner_id=authenticated_user_id,
        initial_prompt=body.initial_prompt,
    )
    return to_session_response(result.session)


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
