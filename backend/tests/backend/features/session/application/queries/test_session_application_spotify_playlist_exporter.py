import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from backend.features.oauth_connections.application import (
    SpotifyConnectionNotFoundException,
    SpotifyTokenRevokedException,
)
from backend.features.oauth_connections.application.schemas import SpotifyAccessToken
from backend.features.session.application.ports import (
    PlaylistMetadata,
    PlaylistMetadataGenerator,
    PlaylistMetadataTrack,
)
from backend.features.session.application.spotify_playlist_exporter import (
    SessionSpotifyPlaylistExporter,
)
from backend.features.session.domain import (
    Session,
    SessionExportRequiresSpotifyConnectionError,
    SessionRepository,
)
from backend.features.user.domain import SpotifyAccount, User, UserRepository


class _SessionRepositoryStub(SessionRepository):
    def __init__(self, session: Session) -> None:
        self._session = session
        self.saved_sessions: list[Session] = []

    async def get_by_id(self, session_id: UUID) -> Session:
        assert session_id == self._session.id
        return self._session

    async def create(self, *, session: Session) -> Session:
        raise AssertionError("Not used in this test")

    async def save(self, *, session: Session) -> Session:
        self.saved_sessions.append(session)
        return session

    async def update(self, session_id: UUID, title: str | None) -> Session:
        raise AssertionError("Not used in this test")

    async def delete(self, session_id: UUID) -> None:
        raise AssertionError("Not used in this test")


class _UserRepositoryStub(UserRepository):
    def __init__(self, user: User | None) -> None:
        self._user = user

    async def get_by_id(self, *, user_id: UUID) -> User | None:
        if self._user is None:
            return None
        assert user_id == self._user.id
        return self._user

    async def delete_by_id(self, *, user_id: UUID) -> bool:
        raise AssertionError("Not used in this test")

    async def count_sessions_for_user(self, *, user_id: UUID) -> int:
        raise AssertionError("Not used in this test")

    async def get_by_auth_identity(self, *, provider, subject: str) -> User | None:
        raise AssertionError("Not used in this test")

    async def create(self, *, user: User) -> User:
        raise AssertionError("Not used in this test")

    async def update(self, *, user: User) -> User:
        raise AssertionError("Not used in this test")

    async def create_with_auth_identity(self, *, user: User, auth_identity) -> User:
        raise AssertionError("Not used in this test")


class _MetadataGeneratorStub(PlaylistMetadataGenerator):
    def __init__(self) -> None:
        self.received_tracks: list[PlaylistMetadataTrack] | None = None

    async def generate(self, tracks: list[PlaylistMetadataTrack]) -> PlaylistMetadata:
        self.received_tracks = tracks
        return PlaylistMetadata(
            name="Roadtrip Mix",
            description="Night drive through city lights",
        )


class _SpotifyPlaylistCreatorStub:
    def __init__(self) -> None:
        self.created_calls: list[tuple[str, str, str]] = []
        self.updated_calls: list[tuple[str, str, str, str]] = []
        self.replaced_calls: list[tuple[str, str, list[str]]] = []

    async def create_private_playlist(
        self,
        *,
        access_token: str,
        name: str,
        description: str,
    ) -> str:
        self.created_calls.append((access_token, name, description))
        return "playlist-new"

    async def update_playlist_details(
        self,
        *,
        access_token: str,
        playlist_id: str,
        name: str,
        description: str,
    ) -> None:
        self.updated_calls.append((access_token, playlist_id, name, description))

    async def replace_playlist_tracks(
        self,
        *,
        access_token: str,
        playlist_id: str,
        track_uris: list[str],
    ) -> None:
        self.replaced_calls.append((access_token, playlist_id, track_uris))


class _TokenServiceStub:
    def __init__(
        self,
        *,
        token: SpotifyAccessToken | None = None,
        error: Exception | None = None,
    ) -> None:
        self._token = token or SpotifyAccessToken(
            access_token="token-123",
            expires_in=3600,
            scope="playlist-modify-private",
        )
        self._error = error
        self.received_user_id: UUID | None = None

    async def get_valid_access_token(self, *, user_id: UUID) -> SpotifyAccessToken:
        self.received_user_id = user_id
        if self._error is not None:
            raise self._error
        return self._token


class TestSessionSpotifyPlaylistExporter:
    def test_export_creates_new_playlist_with_saved_token(self) -> None:
        owner_id = uuid4()
        session = Session(title="Roadtrip", entries=[], owner_id=owner_id)
        session.add_track(
            title="Starlight",
            artist="Muse",
            year=2006,
            spotify_uri="spotify:track:123",
        )

        repository = _SessionRepositoryStub(session=session)
        user_repository = _UserRepositoryStub(
            user=User.restore(
                id=owner_id,
                created_at=datetime.now(UTC),
                name="Mathis",
                spotify=SpotifyAccount.connected_with(is_premium=True),
            )
        )
        metadata_generator = _MetadataGeneratorStub()
        spotify_playlist_creator = _SpotifyPlaylistCreatorStub()
        token_service = _TokenServiceStub()

        exporter = SessionSpotifyPlaylistExporter(
            session_repository=repository,
            user_repository=user_repository,
            metadata_generator=metadata_generator,
            spotify_playlist_creator=spotify_playlist_creator,
            spotify_token_service=token_service,  # type: ignore[arg-type]
        )

        exported = asyncio.run(exporter.export(session_id=session.id, user_id=owner_id))

        assert exported.id == "playlist-new"
        assert exported.track_count == 1
        assert session.playlist is not None
        assert session.playlist.spotify_playlist_id == "playlist-new"
        assert len(repository.saved_sessions) == 1
        assert metadata_generator.received_tracks is not None
        assert len(metadata_generator.received_tracks) == 1
        assert spotify_playlist_creator.created_calls == [
            (
                "token-123",
                "prompster · Roadtrip Mix",
                "Night drive through city lights",
            )
        ]
        assert spotify_playlist_creator.replaced_calls == [
            ("token-123", "playlist-new", ["spotify:track:123"])
        ]

    def test_export_updates_existing_playlist_without_resave(self) -> None:
        owner_id = uuid4()
        session = Session(title="Roadtrip", entries=[], owner_id=owner_id)
        track = session.add_track(
            title="Starlight",
            artist="Muse",
            year=2006,
            spotify_uri="spotify:track:123",
        )
        assert track.spotify_uri == "spotify:track:123"
        assert session.playlist is not None
        session.playlist.spotify_playlist_id = "playlist-existing"

        repository = _SessionRepositoryStub(session=session)
        user_repository = _UserRepositoryStub(
            user=User.restore(
                id=owner_id,
                created_at=datetime.now(UTC),
                name="Mathis",
                spotify=SpotifyAccount.connected_with(is_premium=True),
            )
        )
        spotify_playlist_creator = _SpotifyPlaylistCreatorStub()

        exporter = SessionSpotifyPlaylistExporter(
            session_repository=repository,
            user_repository=user_repository,
            metadata_generator=_MetadataGeneratorStub(),
            spotify_playlist_creator=spotify_playlist_creator,
            spotify_token_service=_TokenServiceStub(),  # type: ignore[arg-type]
        )

        exported = asyncio.run(exporter.export(session_id=session.id, user_id=owner_id))

        assert exported.id == "playlist-existing"
        assert repository.saved_sessions == []
        assert spotify_playlist_creator.created_calls == []
        assert spotify_playlist_creator.updated_calls == [
            (
                "token-123",
                "playlist-existing",
                "prompster · Roadtrip Mix",
                "Night drive through city lights",
            )
        ]
        assert spotify_playlist_creator.replaced_calls == [
            ("token-123", "playlist-existing", ["spotify:track:123"])
        ]

    def test_export_maps_token_failures_to_spotify_connection_error(self) -> None:
        owner_id = uuid4()
        session = Session(title="Roadtrip", entries=[], owner_id=owner_id)
        session.add_track(
            title="Starlight",
            artist="Muse",
            year=2006,
            spotify_uri="spotify:track:123",
        )

        exporter = SessionSpotifyPlaylistExporter(
            session_repository=_SessionRepositoryStub(session=session),
            user_repository=_UserRepositoryStub(
                user=User.restore(
                    id=owner_id,
                    created_at=datetime.now(UTC),
                    name="Mathis",
                    spotify=SpotifyAccount.connected_with(is_premium=True),
                )
            ),
            metadata_generator=_MetadataGeneratorStub(),
            spotify_playlist_creator=_SpotifyPlaylistCreatorStub(),
            spotify_token_service=_TokenServiceStub(
                error=SpotifyTokenRevokedException()
            ),  # type: ignore[arg-type]
        )

        with pytest.raises(
            SessionExportRequiresSpotifyConnectionError,
            match="no connected Spotify account",
        ):
            asyncio.run(exporter.export(session_id=session.id, user_id=owner_id))

        exporter_with_missing_connection = SessionSpotifyPlaylistExporter(
            session_repository=_SessionRepositoryStub(session=session),
            user_repository=_UserRepositoryStub(
                user=User.restore(
                    id=owner_id,
                    created_at=datetime.now(UTC),
                    name="Mathis",
                    spotify=SpotifyAccount.connected_with(is_premium=True),
                )
            ),
            metadata_generator=_MetadataGeneratorStub(),
            spotify_playlist_creator=_SpotifyPlaylistCreatorStub(),
            spotify_token_service=_TokenServiceStub(
                error=SpotifyConnectionNotFoundException()
            ),  # type: ignore[arg-type]
        )

        with pytest.raises(
            SessionExportRequiresSpotifyConnectionError,
            match="no connected Spotify account",
        ):
            asyncio.run(
                exporter_with_missing_connection.export(
                    session_id=session.id,
                    user_id=owner_id,
                )
            )
