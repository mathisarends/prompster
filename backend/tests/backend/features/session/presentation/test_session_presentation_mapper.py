from uuid import uuid4

import pytest
from backend.features.session.domain import (
    DECIDE_FOR_ME_OPTION,
    ImageAttachment,
    Session,
)
from backend.features.session.presentation.mapper import (
    spotify_track_id_from_uri,
    to_session_image_attachment_references,
    to_session_message_attachments,
    to_session_response,
)
from backend.features.session.presentation.schemas import (
    ImageAttachmentReferenceRequest,
    SessionMessageAttachmentKind,
    SessionMessageAttachmentRequest,
)


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


def test_to_session_response_maps_image_attachments_with_signed_urls() -> None:
    owner_id = uuid4()
    session = Session(title="Roadtrip", entries=[], owner_id=owner_id)
    message = session.add_user_message("check this")
    message.image_attachments = (
        ImageAttachment(
            id=uuid4(),
            storage_key="sessions/a/messages/b/attachments/c.png",
            content_type="image/png",
            file_name="screen.png",
            size_bytes=128,
        ),
    )

    response = to_session_response(
        session,
        image_urls_by_storage_key={
            "sessions/a/messages/b/attachments/c.png": "https://signed.example/c.png"
        },
    )

    first_entry = response.entries[0]
    assert first_entry.kind == "user_message"
    assert first_entry.image_attachments == ["https://signed.example/c.png"]


def test_to_session_response_maps_all_onboarding_questions_with_answers() -> None:
    session = Session(title="Roadtrip", entries=[], owner_id=uuid4())
    answered_question = session.add_onboarding_question(
        question_text="Who is joining?",
        options=("Friends", "Family"),
    )
    open_question = session.add_onboarding_question(
        question_text="Which mood?",
        hint="A focused mood makes the deck easier to tune.",
        options=("Relaxed", "Energetic"),
        is_last_question=True,
    )
    session.answer_onboarding_question(
        question_id=answered_question.id,
        answer="Friends",
    )

    response = to_session_response(session)

    assert len(response.onboarding_questions) == 2

    answered = response.onboarding_questions[0]
    assert answered.id == answered_question.id
    assert answered.sequence_number == 1
    assert answered.is_answered is True
    assert answered.answers == ["Friends"]

    still_open = response.onboarding_questions[1]
    assert still_open.id == open_question.id
    assert still_open.sequence_number == 2
    assert still_open.question_text == "Which mood?"
    assert still_open.hint == "A focused mood makes the deck easier to tune."
    assert still_open.options == [
        "Relaxed",
        "Energetic",
        DECIDE_FOR_ME_OPTION,
    ]
    assert still_open.is_last_question is True
    assert still_open.is_answered is False
    assert still_open.answers == []


def test_to_session_message_attachments_maps_request_models() -> None:
    attachments = to_session_message_attachments(
        [
            SessionMessageAttachmentRequest(
                kind=SessionMessageAttachmentKind.SPOTIFY_ARTIST,
                external_id="artist-1",
                title="Artist 1",
                subtitle="Pop",
                image_url="https://example.com/artist.png",
                spotify_id="spotify-artist-1",
            )
        ]
    )

    assert attachments[0].external_id == "artist-1"
    assert attachments[0].spotify_id == "spotify-artist-1"


def test_to_session_image_attachment_references_maps_request_models() -> None:
    attachment_id = uuid4()

    attachments = to_session_image_attachment_references(
        [
            ImageAttachmentReferenceRequest(
                id=attachment_id,
                storage_key="users/a/stash/image.png",
                content_type="image/png",
                file_name="image.png",
                size_bytes=123,
            )
        ]
    )

    assert attachments[0].id == attachment_id
    assert attachments[0].storage_key == "users/a/stash/image.png"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("spotify:track:track-id", "track-id"),
        ("https://open.spotify.com/track/track-id?si=abc", "track-id"),
        ("track-id", "track-id"),
        ("spotify:album:album-id", None),
        ("", None),
    ],
)
def test_spotify_track_id_from_uri(value: str, expected: str | None) -> None:
    assert spotify_track_id_from_uri(value) == expected
