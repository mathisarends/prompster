from backend.features.spotify.domain import (
    InvalidSpotifyTrackUriError,
    SpotifySearchType,
    SpotifyTrack,
    SpotifyTrackNotFoundError,
    SpotifyTrackYearMissingError,
    SpotifyUnifiedSearchResult,
)
from backend.features.spotify.application.ports import SpotifySearchGateway


class SpotifySearch:
    def __init__(self, gateway: SpotifySearchGateway) -> None:
        self._gateway = gateway

    async def search(
        self,
        *,
        query: str,
        limit: int = 20,
        types: set[SpotifySearchType] | None = None,
        requester_id: str | None = None,
    ) -> SpotifyUnifiedSearchResult:
        return await self._gateway.search(
            query=query,
            limit=limit,
            types=types,
            requester_id=requester_id,
        )

    async def get_track(self, *, spotify_uri: str) -> SpotifyTrack:
        track_id = _spotify_track_id_from_uri(spotify_uri)
        if track_id is None:
            raise InvalidSpotifyTrackUriError

        track = await self._gateway.get_track_by_id(track_id=track_id)
        if track is None:
            raise SpotifyTrackNotFoundError
        if track.year is None:
            raise SpotifyTrackYearMissingError
        return track


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
