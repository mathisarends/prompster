import asyncio
from uuid import UUID, uuid4

import pytest

from backend.features.session.application.ports import (
    PlaylistDeckGenerator,
    PlaylistDeckTrack,
)
from backend.features.session.application.queries.session_exporter import (
    SessionPlaylistExporter,
)
from backend.features.session.domain import (
    Session,
    SessionAccessDeniedError,
    SessionPlaylistEmptyError,
    SessionRepository,
)


class _SessionRepositoryStub(SessionRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    async def get_by_id(self, session_id: UUID) -> Session:
        assert session_id == self._session.id
        return self._session

    async def create(self, *, session: Session) -> Session:
        raise AssertionError("Not used in this test")

    async def save(self, *, session: Session) -> Session:
        raise AssertionError("Not used in this test")

    async def update(self, session_id: UUID, title: str | None) -> Session:
        raise AssertionError("Not used in this test")

    async def delete(self, session_id: UUID) -> None:
        raise AssertionError("Not used in this test")


class _DeckGeneratorStub(PlaylistDeckGenerator):
    def __init__(self, pdf_bytes: bytes = b"PDF") -> None:
        self._pdf_bytes = pdf_bytes
        self.received_tracks: list[PlaylistDeckTrack] | None = None

    async def generate(self, tracks: list[PlaylistDeckTrack]) -> bytes:
        self.received_tracks = tracks
        return self._pdf_bytes


class TestSessionPlaylistExporter:
    def test_export_generates_deck_from_playlist(self) -> None:
        owner_id = uuid4()
        session = Session(title="Roadtrip", messages=[], owner_id=owner_id)
        session.add_track(
            title="Insomnia",
            artist="Faithless",
            year=1995,
            cover_url=None,
        )
        repository = _SessionRepositoryStub(session=session)
        generator = _DeckGeneratorStub(pdf_bytes=b"PDF_BYTES")
        exporter = SessionPlaylistExporter(
            session_repository=repository,
            playlist_deck_generator=generator,
        )

        result = asyncio.run(exporter.export(session_id=session.id, user_id=owner_id))

        assert result == b"PDF_BYTES"
        assert generator.received_tracks is not None
        assert len(generator.received_tracks) == 1
        assert generator.received_tracks[0].title == "Insomnia"
        assert generator.received_tracks[0].artist_names == "Faithless"
        assert generator.received_tracks[0].release_year == "1995"
        assert generator.received_tracks[0].spotify_url.startswith(
            "https://open.spotify.com/search/"
        )

    def test_export_raises_when_playlist_empty(self) -> None:
        owner_id = uuid4()
        session = Session(title="Roadtrip", messages=[], owner_id=owner_id)
        repository = _SessionRepositoryStub(session=session)
        generator = _DeckGeneratorStub()
        exporter = SessionPlaylistExporter(
            session_repository=repository,
            playlist_deck_generator=generator,
        )

        with pytest.raises(SessionPlaylistEmptyError, match="no playlist tracks"):
            asyncio.run(exporter.export(session_id=session.id, user_id=owner_id))

    def test_export_raises_for_unauthorized_user(self) -> None:
        session = Session(title="Roadtrip", messages=[], owner_id=uuid4())
        repository = _SessionRepositoryStub(session=session)
        generator = _DeckGeneratorStub()
        exporter = SessionPlaylistExporter(
            session_repository=repository,
            playlist_deck_generator=generator,
        )

        with pytest.raises(SessionAccessDeniedError, match="does not have access"):
            asyncio.run(exporter.export(session_id=session.id, user_id=uuid4()))
