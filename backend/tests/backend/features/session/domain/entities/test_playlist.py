from datetime import datetime, timezone
from uuid import UUID, uuid4

from backend.features.session.domain import Playlist, PlaylistTrack


def assert_utc_datetime(value: datetime) -> None:
    assert value.tzinfo is not None
    assert value.utcoffset() == timezone.utc.utcoffset(None)


class TestSessionDomainPlaylistEntities:
    def test_playlist_track_generates_id_and_utc_created_at_by_default(self) -> None:
        track = PlaylistTrack(title="Starlight", artist="Muse")

        assert isinstance(track.id, UUID)
        assert_utc_datetime(track.created_at)

    def test_playlist_track_assigns_constructor_fields(self) -> None:
        track_id: UUID = uuid4()
        created_time = datetime(2026, 1, 1, tzinfo=timezone.utc)

        track = PlaylistTrack(
            id=track_id,
            title="Starlight",
            artist="Muse",
            year=2006,
            cover_url="https://example.com/starlight.jpg",
            created_time=created_time,
        )

        assert track.id == track_id
        assert track.created_at == created_time
        assert track.title == "Starlight"
        assert track.artist == "Muse"
        assert track.year == 2006
        assert track.cover_url == "https://example.com/starlight.jpg"

    def test_playlist_assigns_tracks_and_name(self) -> None:
        track = PlaylistTrack(title="Teardrop", artist="Massive Attack")

        playlist = Playlist(tracks=[track], name="Favorites")

        assert playlist.name == "Favorites"
        assert playlist.tracks == [track]

    def test_playlist_keeps_explicit_entity_identity(self) -> None:
        playlist_id = uuid4()
        created_time = datetime(2026, 2, 2, tzinfo=timezone.utc)

        playlist = Playlist(tracks=[], id=playlist_id, created_time=created_time)

        assert playlist.id == playlist_id
        assert playlist.created_at == created_time
