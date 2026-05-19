from urllib.parse import quote_plus
from uuid import UUID

from backend.features.session.application.ports import (
    PlaylistDeckGenerator,
    PlaylistDeckTrack,
)
from backend.features.session.domain import (
    PlaylistTrack,
    Session,
    SessionPlaylistEmptyError,
    SessionRepository,
)


class SessionPlaylistExporter:
    def __init__(
        self,
        session_repository: SessionRepository,
        playlist_deck_generator: PlaylistDeckGenerator,
    ) -> None:
        self._session_repository = session_repository
        self._playlist_deck_generator = playlist_deck_generator

    async def export(self, *, session_id: UUID, user_id: UUID) -> bytes:
        session = await self._get_authorized(session_id=session_id, user_id=user_id)
        playlist = session.playlist
        if playlist is None or not playlist.tracks:
            raise SessionPlaylistEmptyError(
                f"Session {session.id} has no playlist tracks to export."
            )

        tracks = [self._to_deck_track(track) for track in playlist.tracks]
        return await self._playlist_deck_generator.generate(tracks)

    async def _get_authorized(self, *, session_id: UUID, user_id: UUID) -> Session:
        session = await self._session_repository.get_by_id(session_id=session_id)
        session.has_access(user_id)
        return session

    def _to_deck_track(self, track: PlaylistTrack) -> PlaylistDeckTrack:
        query = quote_plus(f"{track.title} {track.artist}".strip())
        spotify_search_url = f"https://open.spotify.com/search/{query}"
        year = str(track.year) if track.year is not None else ""
        return PlaylistDeckTrack(
            title=track.title,
            artist_names=track.artist,
            release_year=year,
            spotify_url=spotify_search_url,
        )
