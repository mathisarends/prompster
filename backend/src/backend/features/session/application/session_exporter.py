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
from backend.platform.storage.port import ObjectStorage

_CARDS_PER_DECK_PAGE = 15
_PDF_PAGES_PER_CARD_BATCH = 2


class SessionPlaylistExporter:
    def __init__(
        self,
        session_repository: SessionRepository,
        playlist_deck_generator: PlaylistDeckGenerator,
        storage_backend: ObjectStorage,
    ) -> None:
        self._session_repository = session_repository
        self._playlist_deck_generator = playlist_deck_generator
        self._storage_backend = storage_backend

    async def export(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        page_limit: int | None = None,
    ) -> bytes:
        session = await self._get_authorized(session_id=session_id, user_id=user_id)
        playlist = session.playlist
        if playlist is None or not playlist.tracks:
            raise SessionPlaylistEmptyError(
                f"Session {session.id} has no playlist tracks to export."
            )

        playlist_tracks = playlist.tracks
        if page_limit is not None:
            deck_batches = (page_limit + _PDF_PAGES_PER_CARD_BATCH - 1) // 2
            playlist_tracks = playlist_tracks[: deck_batches * _CARDS_PER_DECK_PAGE]

        fingerprint = session.playlist_fingerprint
        cached = await self._get_cached_pdf(
            session=session, page_limit=page_limit, fingerprint=fingerprint
        )
        if cached is not None:
            return cached

        tracks = [self._to_deck_track(track) for track in playlist_tracks]
        pdf = await self._playlist_deck_generator.generate(
            tracks,
            page_limit=page_limit,
        )
        if page_limit is None and fingerprint is not None:
            storage_key = self._build_storage_key(
                user_id=user_id,
                session_id=session.id,
                fingerprint=fingerprint,
            )
            await self._storage_backend.upload_bytes(
                path=storage_key,
                data=pdf,
                content_type="application/pdf",
            )
            session.set_playlist_pdf_export(
                storage_key=storage_key,
                fingerprint=fingerprint,
            )
            await self._session_repository.save(session=session)
        return pdf

    async def _get_cached_pdf(
        self,
        *,
        session: Session,
        page_limit: int | None,
        fingerprint: str | None,
    ) -> bytes | None:
        if (
            page_limit is None
            and fingerprint is not None
            and session.playlist_pdf_fingerprint == fingerprint
            and session.playlist_pdf_storage_key is not None
            and await self._storage_backend.exists(session.playlist_pdf_storage_key)
        ):
            return await self._storage_backend.download_bytes(
                session.playlist_pdf_storage_key
            )
        return None

    async def _get_authorized(self, *, session_id: UUID, user_id: UUID) -> Session:
        session = await self._session_repository.get_by_id(session_id=session_id)
        session.has_access(user_id)
        return session

    def _to_deck_track(self, track: PlaylistTrack) -> PlaylistDeckTrack:
        year = str(track.year) if track.year is not None else ""
        return PlaylistDeckTrack(
            title=track.title,
            artist_names=track.artist,
            release_year=year,
            spotify_url=self._build_spotify_url(track),
        )

    @staticmethod
    def _build_spotify_url(track: PlaylistTrack) -> str:
        if track.spotify_uri and track.spotify_uri.startswith("spotify:track:"):
            track_id = track.spotify_uri.removeprefix("spotify:track:")
            return f"https://open.spotify.com/track/{track_id}"
        query = quote_plus(f"{track.title} {track.artist}".strip())
        return f"https://open.spotify.com/search/{query}"

    @staticmethod
    def _build_storage_key(
        *,
        user_id: UUID,
        session_id: UUID,
        fingerprint: str,
    ) -> str:
        return f"users/{user_id}/chat/{session_id}/exports/playlist-{fingerprint}.pdf"
