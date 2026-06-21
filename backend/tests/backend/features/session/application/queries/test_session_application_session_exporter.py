import asyncio
from uuid import UUID, uuid4

import pytest

from backend.features.session.application.ports import (
    PlaylistDeckGenerator,
    PlaylistDeckTrack,
)
from backend.features.session.application.session_exporter import (
    SessionPlaylistExporter,
)
from backend.features.session.domain import (
    Session,
    SessionAccessDeniedError,
    SessionPlaylistEmptyError,
    SessionRepository,
)
from backend.infrastructure.storage import StorageBackend
from backend.infrastructure.storage.views import StorageFile, UploadResponse


class _SessionRepositoryStub(SessionRepository):
    def __init__(self, session: Session) -> None:
        self._session = session
        self.saved_session: Session | None = None

    async def get_by_id(self, session_id: UUID) -> Session:
        assert session_id == self._session.id
        return self._session

    async def create(self, *, session: Session) -> Session:
        raise AssertionError("Not used in this test")

    async def save(self, *, session: Session) -> Session:
        self.saved_session = session
        return session

    async def update(self, session_id: UUID, title: str | None) -> Session:
        raise AssertionError("Not used in this test")

    async def delete(self, session_id: UUID) -> None:
        raise AssertionError("Not used in this test")


class _DeckGeneratorStub(PlaylistDeckGenerator):
    def __init__(self, pdf_bytes: bytes = b"PDF") -> None:
        self._pdf_bytes = pdf_bytes
        self.received_tracks: list[PlaylistDeckTrack] | None = None
        self.received_page_limit: int | None = None

    async def generate(
        self,
        tracks: list[PlaylistDeckTrack],
        *,
        page_limit: int | None = None,
    ) -> bytes:
        self.received_tracks = tracks
        self.received_page_limit = page_limit
        return self._pdf_bytes


class _StorageBackendStub(StorageBackend):
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.uploaded_path: str | None = None
        self.uploaded_content_type: str | None = None

    async def upload_bytes(
        self,
        path: str,
        data: bytes,
        content_type: str | None = None,
    ) -> UploadResponse:
        self.files[path] = data
        self.uploaded_path = path
        self.uploaded_content_type = content_type
        return UploadResponse(storage_path=path)

    async def download_bytes(self, path: str) -> bytes:
        return self.files[path]

    async def delete(self, path: str) -> None:
        self.files.pop(path, None)

    async def delete_folder(self, path: str) -> None:
        for key in list(self.files):
            if key.startswith(path):
                del self.files[key]

    async def move(self, source_path: str, destination_path: str) -> None:
        self.files[destination_path] = self.files.pop(source_path)

    async def list_files(self, path: str = "") -> list[StorageFile]:
        return [StorageFile(name=key) for key in self.files if key.startswith(path)]

    async def create_signed_url(self, path: str, ttl_seconds: int = 3600) -> str:
        return f"https://signed.example/{path}?ttl={ttl_seconds}"

    async def exists(self, path: str) -> bool:
        return path in self.files


class TestSessionPlaylistExporter:
    def test_export_generates_deck_from_playlist(self) -> None:
        owner_id = uuid4()
        session = Session(title="Roadtrip", entries=[], owner_id=owner_id)
        session.add_track(
            title="Insomnia",
            artist="Faithless",
            year=1995,
            spotify_uri="spotify:track:7uv632EkfwYhXoqf8rhYrg",
            cover_url=None,
        )
        repository = _SessionRepositoryStub(session=session)
        generator = _DeckGeneratorStub(pdf_bytes=b"PDF_BYTES")
        storage = _StorageBackendStub()
        exporter = SessionPlaylistExporter(
            session_repository=repository,
            playlist_deck_generator=generator,
            storage_backend=storage,
        )

        result = asyncio.run(exporter.export(session_id=session.id, user_id=owner_id))

        assert result == b"PDF_BYTES"
        assert generator.received_tracks is not None
        assert len(generator.received_tracks) == 1
        assert generator.received_tracks[0].title == "Insomnia"
        assert generator.received_tracks[0].artist_names == "Faithless"
        assert generator.received_tracks[0].release_year == "1995"
        assert (
            generator.received_tracks[0].spotify_url
            == "https://open.spotify.com/track/7uv632EkfwYhXoqf8rhYrg"
        )
        assert generator.received_page_limit is None
        assert storage.uploaded_content_type == "application/pdf"
        assert session.playlist_pdf_storage_key == storage.uploaded_path
        assert session.playlist_pdf_fingerprint == session.playlist_fingerprint
        assert repository.saved_session is session

    def test_export_falls_back_to_search_url_when_track_has_no_spotify_uri(
        self,
    ) -> None:
        owner_id = uuid4()
        session = Session(title="Roadtrip", entries=[], owner_id=owner_id)
        session.add_track(
            title="Insomnia",
            artist="Faithless",
            year=1995,
            cover_url=None,
        )
        repository = _SessionRepositoryStub(session=session)
        generator = _DeckGeneratorStub(pdf_bytes=b"PDF_BYTES")
        storage = _StorageBackendStub()
        exporter = SessionPlaylistExporter(
            session_repository=repository,
            playlist_deck_generator=generator,
            storage_backend=storage,
        )

        asyncio.run(exporter.export(session_id=session.id, user_id=owner_id))

        assert generator.received_tracks is not None
        assert generator.received_tracks[0].spotify_url.startswith(
            "https://open.spotify.com/search/"
        )

    def test_export_can_limit_generated_preview_pages(self) -> None:
        owner_id = uuid4()
        session = Session(title="Roadtrip", entries=[], owner_id=owner_id)
        for index in range(39):
            session.add_track(
                title=f"Track {index}",
                artist="Artist",
                year=2000 + index,
                cover_url=None,
            )
        repository = _SessionRepositoryStub(session=session)
        generator = _DeckGeneratorStub(pdf_bytes=b"PDF_BYTES")
        storage = _StorageBackendStub()
        exporter = SessionPlaylistExporter(
            session_repository=repository,
            playlist_deck_generator=generator,
            storage_backend=storage,
        )

        result = asyncio.run(
            exporter.export(session_id=session.id, user_id=owner_id, page_limit=2)
        )

        assert result == b"PDF_BYTES"
        assert generator.received_tracks is not None
        assert len(generator.received_tracks) == 15
        assert generator.received_page_limit == 2
        assert repository.saved_session is None
        assert storage.uploaded_path is None

    def test_export_reuses_cached_pdf_when_playlist_fingerprint_matches(self) -> None:
        owner_id = uuid4()
        session = Session(title="Roadtrip", entries=[], owner_id=owner_id)
        session.add_track(
            title="Insomnia",
            artist="Faithless",
            year=1995,
            cover_url=None,
        )
        storage_key = "users/u/chat/s/exports/playlist-existing.pdf"
        session.set_playlist_pdf_export(
            storage_key=storage_key,
            fingerprint=session.playlist_fingerprint or "",
        )
        repository = _SessionRepositoryStub(session=session)
        generator = _DeckGeneratorStub(pdf_bytes=b"NEW_PDF")
        storage = _StorageBackendStub()
        storage.files[storage_key] = b"CACHED_PDF"
        exporter = SessionPlaylistExporter(
            session_repository=repository,
            playlist_deck_generator=generator,
            storage_backend=storage,
        )

        result = asyncio.run(exporter.export(session_id=session.id, user_id=owner_id))

        assert result == b"CACHED_PDF"
        assert generator.received_tracks is None
        assert repository.saved_session is None

    def test_export_raises_when_playlist_empty(self) -> None:
        owner_id = uuid4()
        session = Session(title="Roadtrip", entries=[], owner_id=owner_id)
        repository = _SessionRepositoryStub(session=session)
        generator = _DeckGeneratorStub()
        storage = _StorageBackendStub()
        exporter = SessionPlaylistExporter(
            session_repository=repository,
            playlist_deck_generator=generator,
            storage_backend=storage,
        )

        with pytest.raises(SessionPlaylistEmptyError, match="no playlist tracks"):
            asyncio.run(exporter.export(session_id=session.id, user_id=owner_id))

    def test_export_raises_for_unauthorized_user(self) -> None:
        session = Session(title="Roadtrip", entries=[], owner_id=uuid4())
        repository = _SessionRepositoryStub(session=session)
        generator = _DeckGeneratorStub()
        storage = _StorageBackendStub()
        exporter = SessionPlaylistExporter(
            session_repository=repository,
            playlist_deck_generator=generator,
            storage_backend=storage,
        )

        with pytest.raises(SessionAccessDeniedError, match="does not have access"):
            asyncio.run(exporter.export(session_id=session.id, user_id=uuid4()))
