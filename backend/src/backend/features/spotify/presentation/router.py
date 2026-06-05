from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query, status

from backend.features.auth.presentation.dependencies import AuthenticatedUserId
from backend.features.spotify.application.ports import SpotifySearch, SpotifySearchType
from backend.features.spotify.presentation.mapper import (
    to_spotify_artist_response,
    to_spotify_playlist_response,
    to_spotify_track_response,
)
from backend.features.spotify.presentation.schemas import (
    SpotifyUnifiedSearchResponse,
)
from backend.presentation.errors import ErrorDto

spotify_router = APIRouter(route_class=DishkaRoute, prefix="/spotify", tags=["spotify"])

_auth_errors = {
    status.HTTP_401_UNAUTHORIZED: {"model": ErrorDto},
    status.HTTP_403_FORBIDDEN: {"model": ErrorDto},
}


@spotify_router.get(
    "/search",
    response_model=SpotifyUnifiedSearchResponse,
    status_code=status.HTTP_200_OK,
    operation_id="search_spotify",
    responses=_auth_errors,
)
async def search_spotify(
    authenticated_user_id: AuthenticatedUserId,
    spotify_search: FromDishka[SpotifySearch],
    query: str = Query(min_length=1, max_length=200, description="Search query"),
    limit: int = Query(default=20, ge=1, le=50),
    types: set[SpotifySearchType] = Query(
        default={
            SpotifySearchType.TRACK,
            SpotifySearchType.PLAYLIST,
            SpotifySearchType.ARTIST,
        },
        description="Search resource types",
    ),
) -> SpotifyUnifiedSearchResponse:
    search_results = await spotify_search.search(
        query=query,
        limit=limit,
        types=types,
        requester_id=str(authenticated_user_id),
    )

    return SpotifyUnifiedSearchResponse(
        tracks=[to_spotify_track_response(track) for track in search_results.tracks],
        playlists=[
            to_spotify_playlist_response(playlist)
            for playlist in search_results.playlists
        ],
        artists=[
            to_spotify_artist_response(artist) for artist in search_results.artists
        ],
    )
