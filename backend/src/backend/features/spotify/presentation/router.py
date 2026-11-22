from typing import Annotated

from backend.features.auth.presentation.dependencies import AuthenticatedUserId
from backend.features.auth.presentation.exceptions import (
    AUTHENTICATION_REQUIRED_ERROR,
)
from backend.features.spotify.application import SpotifySearch, SpotifySearchType
from backend.features.spotify.presentation.mapper import (
    to_spotify_unified_search_response,
)
from backend.features.spotify.presentation.schemas import (
    SpotifyUnifiedSearchResponse,
)
from fastapi import Query, status
from fastapi_canon import APIRouter, Inject

spotify_router = APIRouter(
    prefix="/spotify",
    tags=["spotify"],
    raises=(AUTHENTICATION_REQUIRED_ERROR,),
)
_DEFAULT_SEARCH_TYPES = (
    SpotifySearchType.TRACK,
    SpotifySearchType.PLAYLIST,
    SpotifySearchType.ARTIST,
)


@spotify_router.get(
    "/search",
    response_model=SpotifyUnifiedSearchResponse,
    status_code=status.HTTP_200_OK,
    operation_id="search_spotify",
)
async def search_spotify(
    authenticated_user_id: AuthenticatedUserId,
    spotify_search: Inject[SpotifySearch],
    query: Annotated[
        str, Query(min_length=1, max_length=200, description="Search query")
    ],
    types: Annotated[
        set[SpotifySearchType],
        Query(description="Search resource types"),
    ] = _DEFAULT_SEARCH_TYPES,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> SpotifyUnifiedSearchResponse:
    search_results = await spotify_search.search(
        query=query,
        limit=limit,
        types=types,
        requester_id=str(authenticated_user_id),
    )

    return to_spotify_unified_search_response(search_results)
