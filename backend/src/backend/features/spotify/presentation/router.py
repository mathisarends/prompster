from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query, status

from backend.features.auth.presentation.dependencies import AuthenticatedUserId
from backend.features.spotify.application import SpotifyService
from backend.features.spotify.presentation.mapper import to_spotify_track_response
from backend.features.spotify.presentation.schemas import SpotifyTrackSearchResponse
from backend.presentation.errors import ErrorDto

spotify_router = APIRouter(
    route_class=DishkaRoute, prefix="/sessions", tags=["spotify"]
)

_auth_errors = {
    status.HTTP_401_UNAUTHORIZED: {"model": ErrorDto},
    status.HTTP_403_FORBIDDEN: {"model": ErrorDto},
}


@spotify_router.get(
    "/spotify-tracks",
    response_model=SpotifyTrackSearchResponse,
    status_code=status.HTTP_200_OK,
    operation_id="search_spotify_tracks",
    responses=_auth_errors,
)
async def search_spotify_tracks(
    _authenticated_user_id: AuthenticatedUserId,  # keep to ensure authentication
    service: FromDishka[SpotifyService],
    query: str = Query(min_length=1, max_length=200, description="Search query"),
    limit: int = Query(default=20, ge=1, le=50),
) -> SpotifyTrackSearchResponse:
    tracks = await service.search_tracks(query=query, limit=limit)
    return SpotifyTrackSearchResponse(
        items=[to_spotify_track_response(track) for track in tracks],
    )
