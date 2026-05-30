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


def test_to_session_response_maps_only_open_onboarding_questions() -> None:
    session = Session(title="Roadtrip", entries=[], owner_id=uuid4())
    answered_question = session.add_onboarding_question(
        question_text="Who is joining?",
        options=("Friends", "Family"),
    )
    open_question = session.add_onboarding_question(
        question_text="Which mood?",
        options=("Relaxed", "Energetic"),
        is_last_question=True,
    )
    session.answer_onboarding_question(
        question_id=answered_question.id,
        answer="Friends",
    )

    response = to_session_response(session)

    assert len(response.open_onboarding_questions) == 1
    assert response.open_onboarding_questions[0].id == open_question.id
    assert response.open_onboarding_questions[0].sequence_number == 2
    assert response.open_onboarding_questions[0].question_text == "Which mood?"
    assert response.open_onboarding_questions[0].options == ["Relaxed", "Energetic"]
    assert response.open_onboarding_questions[0].is_last_question is True
