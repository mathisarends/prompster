from dataclasses import dataclass

from agent.tools.handler.spotify_rendering import (
    format_album,
    format_playlist,
    track_lookup_result,
)


@dataclass
class _Artist:
    name: str
    uri: str


@dataclass
class _Track:
    name: str
    uri: str
    artists: list[_Artist]


@dataclass
class _Album:
    name: str
    uri: str
    artists: list[_Artist]
    release_date: str
    total_tracks: int


@dataclass
class _TrackCount:
    total: int


@dataclass
class _Playlist:
    id: str
    name: str
    items: _TrackCount | None
    tracks: _TrackCount | None = None


class TestSpotifyTrackRendering:
    def test_track_lookup_content_uses_shared_track_markup(self) -> None:
        result = track_lookup_result(
            [
                _Track(
                    name="Take On Me",
                    uri="spotify:track:2WfaOiMkCvy7F5fcp2zZ8L",
                    artists=[
                        _Artist(
                            name="a-ha",
                            uri="spotify:artist:2jzc5TC5TVFLXQlBNiIUzE",
                        )
                    ],
                )
            ],
            release_date_for=lambda _: "1985-10-19",
            cover_url_for=lambda _: "https://i.scdn.co/image/take-on-me.jpg",
        )

        assert result.content == (
            '<track uri="spotify:track:2WfaOiMkCvy7F5fcp2zZ8L" '
            'label="a-ha - Take On Me (1985)" />'
        )
        assert result.tracks[0].title == "Take On Me"
        assert result.tracks[0].cover_url == "https://i.scdn.co/image/take-on-me.jpg"

    def test_album_content_uses_shared_album_markup(self) -> None:
        album = _Album(
            name="The Lexicon of Love",
            uri="spotify:album:6tE4oQ2kYwG7D9w3xB7L8G",
            artists=[
                _Artist(
                    name="ABC",
                    uri="spotify:artist:2P3cjUru4H3fhSXXNxE9kA",
                )
            ],
            release_date="1982-06-21",
            total_tracks=10,
        )

        assert format_album(album) == (
            '<album uri="spotify:album:6tE4oQ2kYwG7D9w3xB7L8G" '
            'label="ABC - The Lexicon of Love (1982)" tracks="10" />'
        )

    def test_playlist_content_uses_shared_playlist_markup(self) -> None:
        playlist = _Playlist(
            id="37i9dQZF1DX4UtSsGT1Sbe",
            name="All Out 80s",
            items=_TrackCount(total=100),
        )

        assert format_playlist(playlist) == (
            '<playlist id="37i9dQZF1DX4UtSsGT1Sbe" label="All Out 80s" tracks="100" />'
        )
