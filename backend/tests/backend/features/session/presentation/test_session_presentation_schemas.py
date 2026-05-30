import pytest
from pydantic import ValidationError

from backend.features.session.presentation.schemas import (
    AddPlaylistTrackRequest,
    SendMessageRequest,
)


class TestSendMessageRequest:
    def test_accepts_content(self) -> None:
        request = SendMessageRequest(content="spiele house")

        assert request.content == "spiele house"

    def test_accepts_attachment_references(self) -> None:
        request = SendMessageRequest(
            content="nimm diese playlist",
            attachments=[
                {
                    "kind": "spotify-playlist",
                    "external_id": "37i9dQZF1DX4dyzvuaRJ0n",
                    "title": "Lo-Fi Beats",
                    "subtitle": "Spotify",
                    "image_url": "https://example.com/image.jpg",
                    "spotify_id": "37i9dQZF1DX4dyzvuaRJ0n",
                }
            ],
        )

        assert len(request.attachments) == 1
        assert request.attachments[0].kind.value == "spotify-playlist"
        assert request.attachments[0].external_id == "37i9dQZF1DX4dyzvuaRJ0n"

    def test_rejects_duplicate_attachments(self) -> None:
        with pytest.raises(ValidationError, match="Duplicate attachments"):
            SendMessageRequest(
                content="duplikat",
                attachments=[
                    {
                        "kind": "spotify-artist",
                        "external_id": "1dfeR4HaWDbWqFHLkxsg1d",
                        "title": "Queen",
                    },
                    {
                        "kind": "spotify-artist",
                        "external_id": "1dfeR4HaWDbWqFHLkxsg1d",
                        "title": "Queen",
                    },
                ],
            )


class TestAddPlaylistTrackRequest:
    def test_requires_year(self) -> None:
        with pytest.raises(ValidationError, match="year"):
            AddPlaylistTrackRequest(title="Starlight", artist="Muse")

    def test_rejects_year_out_of_range(self) -> None:
        with pytest.raises(ValidationError, match="greater than or equal to 1900"):
            AddPlaylistTrackRequest(title="Starlight", artist="Muse", year=1899)
