from uuid import uuid4

from backend.features.session.domain import Session
from backend.features.session.presentation.mapper import to_session_response


def test_to_session_response_maps_references() -> None:
    owner_id = uuid4()
    session = Session(title="Roadtrip", entries=[], owner_id=owner_id)
    playlist_reference = session.add_playlist_reference(
        spotify_playlist_id="37i9dQZF1DX4dyzvuaRJ0n",
        name="Lo-Fi Beats",
        owner="Spotify",
        cover_url="https://example.com/playlist.jpg",
        total_tracks=100,
    )
    artist_reference = session.add_artist_reference(
        spotify_artist_id="1dfeR4HaWDbWqFHLkxsg1d",
        name="Queen",
        image_url="https://example.com/queen.jpg",
        genres=("rock", "glam rock"),
        followers=50_000_000,
        popularity=81,
    )

    response = to_session_response(session)

    assert len(response.playlist_references) == 1
    assert response.playlist_references[0].id == playlist_reference.id
    assert response.playlist_references[0].spotify_playlist_id == (
        "37i9dQZF1DX4dyzvuaRJ0n"
    )
    assert response.playlist_references[0].total_tracks == 100
    assert len(response.artist_references) == 1
    assert response.artist_references[0].id == artist_reference.id
    assert response.artist_references[0].genres == ["rock", "glam rock"]
