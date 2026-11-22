from dataclasses import dataclass
from uuid import UUID

from backend.features.oauth_connections.application import (
    SpotifyConnectionNotFoundException,
    SpotifyTokenRevokedException,
    SpotifyTokenService,
)
from backend.features.session.application.ports import (
    PlaylistMetadataGenerator,
    PlaylistMetadataTrack,
)
from backend.features.session.domain import (
    PlaylistTrack,
    Session,
    SessionExportRequiresSpotifyConnectionError,
    SessionPlaylistEmptyError,
    SessionPlaylistMissingSpotifyTracksError,
    SessionRepository,
)
from backend.features.spotify.application import SpotifyPlaylistCreator
from backend.features.user.domain import UserRepository


@dataclass(frozen=True, slots=True)
class ExportedSpotifyPlaylist:
    id: str
    name: str
    description: str
    url: str
    track_count: int


@dataclass(frozen=True, slots=True)
class SpotifyExportPlan:
    """Everything needed to write the playlist to Spotify.

    Produced by :meth:`SessionSpotifyPlaylistExporter.prepare` — which performs
    all validation up front so domain errors surface as HTTP responses — and
    consumed by :meth:`execute`, where the (retry-prone) Spotify writes happen.
    """

    session: Session
    access_token: str
    name: str
    description: str
    track_uris: list[str]
    existing_playlist_id: str | None


class SessionSpotifyPlaylistExporter:
    def __init__(
        self,
        session_repository: SessionRepository,
        user_repository: UserRepository,
        metadata_generator: PlaylistMetadataGenerator,
        spotify_playlist_creator: SpotifyPlaylistCreator,
        spotify_token_service: SpotifyTokenService,
    ) -> None:
        self._session_repository = session_repository
        self._user_repository = user_repository
        self._metadata_generator = metadata_generator
        self._spotify_playlist_creator = spotify_playlist_creator
        self._spotify_token_service = spotify_token_service

    async def export(
        self, *, session_id: UUID, user_id: UUID
    ) -> ExportedSpotifyPlaylist:
        plan = await self.prepare(session_id=session_id, user_id=user_id)
        return await self.execute(plan)

    async def prepare(self, *, session_id: UUID, user_id: UUID) -> SpotifyExportPlan:
        """Validate the request and build the export plan.

        Runs before any Spotify write so its domain errors propagate as HTTP
        responses rather than mid-stream error events.
        """
        await self._require_spotify_connection(user_id=user_id)
        session = await self._get_authorized(session_id=session_id, user_id=user_id)
        playlist = session.playlist
        if playlist is None or not playlist.tracks:
            raise SessionPlaylistEmptyError(
                f"Session {session.id} has no playlist tracks to export."
            )

        track_uris = [
            track.spotify_uri for track in playlist.tracks if track.spotify_uri
        ]
        if not track_uris:
            raise SessionPlaylistMissingSpotifyTracksError(
                f"Session {session.id} playlist has no tracks linked to Spotify."
            )

        access_token = await self._require_spotify_access_token(user_id=user_id)

        metadata = await self._metadata_generator.generate(
            [self._to_metadata_track(track) for track in playlist.tracks]
        )

        return SpotifyExportPlan(
            session=session,
            access_token=access_token,
            name=self._build_name(metadata.name),
            description=metadata.description[:_DESCRIPTION_MAX_LENGTH],
            track_uris=track_uris,
            existing_playlist_id=playlist.spotify_playlist_id or None,
        )

    async def execute(self, plan: SpotifyExportPlan) -> ExportedSpotifyPlaylist:
        """Write the prepared plan to Spotify. This is where retries happen."""
        if plan.existing_playlist_id:
            playlist_id = await self._update_existing_playlist(
                playlist_id=plan.existing_playlist_id,
                access_token=plan.access_token,
                name=plan.name,
                description=plan.description,
                track_uris=plan.track_uris,
            )
        else:
            playlist_id = await self._create_new_playlist(
                access_token=plan.access_token,
                name=plan.name,
                description=plan.description,
                track_uris=plan.track_uris,
            )
            if plan.session.playlist is not None:
                plan.session.playlist.spotify_playlist_id = playlist_id
            await self._session_repository.save(session=plan.session)

        return ExportedSpotifyPlaylist(
            id=playlist_id,
            name=plan.name,
            description=plan.description,
            url=_PLAYLIST_URL_TEMPLATE.format(playlist_id=playlist_id),
            track_count=len(plan.track_uris),
        )

    async def _require_spotify_connection(self, *, user_id: UUID) -> None:
        user = await self._user_repository.get_by_id(user_id=user_id)
        if user is None or not user.spotify.connected:
            raise SessionExportRequiresSpotifyConnectionError(
                f"User {user_id} has no connected Spotify account."
            )

    async def _require_spotify_access_token(self, *, user_id: UUID) -> str:
        try:
            token = await self._spotify_token_service.get_valid_access_token(
                user_id=user_id,
            )
        except (
            SpotifyConnectionNotFoundException,
            SpotifyTokenRevokedException,
        ) as exc:
            raise SessionExportRequiresSpotifyConnectionError(
                f"User {user_id} has no connected Spotify account."
            ) from exc
        return token.access_token

    async def _create_new_playlist(
        self,
        *,
        access_token: str,
        name: str,
        description: str,
        track_uris: list[str],
    ) -> str:
        playlist_id = await self._spotify_playlist_creator.create_private_playlist(
            access_token=access_token,
            name=name,
            description=description,
        )
        await self._spotify_playlist_creator.replace_playlist_tracks(
            access_token=access_token,
            playlist_id=playlist_id,
            track_uris=track_uris,
        )
        return playlist_id

    async def _update_existing_playlist(
        self,
        *,
        playlist_id: str,
        access_token: str,
        name: str,
        description: str,
        track_uris: list[str],
    ) -> str:
        await self._spotify_playlist_creator.update_playlist_details(
            access_token=access_token,
            playlist_id=playlist_id,
            name=name,
            description=description,
        )
        await self._spotify_playlist_creator.replace_playlist_tracks(
            access_token=access_token,
            playlist_id=playlist_id,
            track_uris=track_uris,
        )
        return playlist_id

    async def _get_authorized(self, *, session_id: UUID, user_id: UUID) -> Session:
        session = await self._session_repository.get_by_id(session_id=session_id)
        session.has_access(user_id)
        return session

    def _build_name(self, generated_name: str) -> str:
        max_suffix = _NAME_MAX_LENGTH - len(_NAME_PREFIX)
        return f"{_NAME_PREFIX}{generated_name.strip()[:max_suffix]}"

    def _to_metadata_track(self, track: PlaylistTrack) -> PlaylistMetadataTrack:
        return PlaylistMetadataTrack(
            title=track.title,
            artist=track.artist,
            year=track.year,
        )


_NAME_PREFIX = "prompster · "


_NAME_MAX_LENGTH = 100


_DESCRIPTION_MAX_LENGTH = 300


_PLAYLIST_URL_TEMPLATE = "https://open.spotify.com/playlist/{playlist_id}"
