import asyncio
import io
import re

import httpx
from PIL import Image

from backend.features.session.application.ports import PlaylistDeckTrack
from backend.features.session.infrastructure.pdf_generator.cover_art import (
    SpotifyCoverArtLoader,
)
from backend.features.session.infrastructure.pdf_generator.renderer import (
    TypstPlaylistDeckGenerator,
)

_PAGE_OBJECT = re.compile(rb"/Type\s*/Page\b")
_CARDS_PER_SHEET = 15


def _cover_response(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("missing"):
        return httpx.Response(404)
    buffer = io.BytesIO()
    image = Image.new("RGB", (64, 64), (30, 60, 220))
    image.save(buffer, format="JPEG")
    return httpx.Response(200, content=buffer.getvalue())


def _track(year: str, *, cover_url: str | None = None) -> PlaylistDeckTrack:
    return PlaylistDeckTrack(
        title="Dancing Queen",
        artist_names="ABBA",
        release_year=year,
        spotify_url="https://open.spotify.com/track/0GjEhVFGZW8afUYGChu3Rr",
        cover_url=cover_url,
    )


def _generate(
    tracks: list[PlaylistDeckTrack], *, page_limit: int | None = None
) -> bytes:
    transport = httpx.MockTransport(_cover_response)
    cover_art_loader = SpotifyCoverArtLoader(transport)
    generator = TypstPlaylistDeckGenerator(cover_art_loader=cover_art_loader)
    return asyncio.run(generator.generate(tracks, page_limit=page_limit))


def _page_count(pdf: bytes) -> int:
    return len(_PAGE_OBJECT.findall(pdf))


class TestTypstPlaylistDeckGenerator:
    def test_generate_renders_a_qr_sheet_and_an_answer_sheet(self) -> None:
        tracks = [_track("1976", cover_url="https://i.scdn.co/image/cover")]

        pdf = _generate(tracks)

        assert pdf.startswith(b"%PDF")
        assert _page_count(pdf) == 2

    def test_generate_draws_every_era_with_and_without_cover(self) -> None:
        tracks = [
            _track("1969", cover_url="https://i.scdn.co/image/cover"),
            _track("1985", cover_url="https://i.scdn.co/image/cover"),
            _track("1996"),
            _track("2019", cover_url="https://i.scdn.co/image/missing"),
            _track(""),
        ]

        pdf = _generate(tracks)

        assert _page_count(pdf) == 2

    def test_generate_starts_new_sheets_after_fifteen_cards(self) -> None:
        tracks = [_track("2000")] * (_CARDS_PER_SHEET + 1)

        pdf = _generate(tracks)

        assert _page_count(pdf) == 4

    def test_generate_stops_at_the_page_limit(self) -> None:
        tracks = [_track("2000")] * (_CARDS_PER_SHEET + 1)

        pdf = _generate(tracks, page_limit=1)

        assert _page_count(pdf) == 1
