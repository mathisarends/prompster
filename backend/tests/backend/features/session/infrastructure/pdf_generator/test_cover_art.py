import asyncio
import io

import httpx
import pytest
from PIL import Image

from backend.features.session.infrastructure.pdf_generator.cover_art import (
    CoverArt,
    SpotifyCoverArtLoader,
)

_COVER_URL = "https://i.scdn.co/image/ab67616d0000b273cover"


def _jpeg(colour: tuple[int, int, int], edge: int = 640) -> bytes:
    buffer = io.BytesIO()
    image = Image.new("RGB", (edge, edge), colour)
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


class _CoverServer:
    def __init__(self, response: httpx.Response) -> None:
        self._response = response
        self.requested_urls: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requested_urls.append(str(request.url))
        return self._response


def _load(server: _CoverServer, urls: list[str | None]) -> list[CoverArt | None]:
    transport = httpx.MockTransport(server)
    loader = SpotifyCoverArtLoader(transport)
    return asyncio.run(loader.load(urls))


class TestSpotifyCoverArtLoader:
    def test_load_returns_print_sized_jpeg_with_palette(self) -> None:
        response = httpx.Response(200, content=_jpeg((30, 60, 220)))
        server = _CoverServer(response)

        covers = _load(server, [_COVER_URL])

        cover = covers[0]
        assert cover is not None
        with Image.open(io.BytesIO(cover.jpeg)) as image:
            assert image.format == "JPEG"
            assert image.size == (400, 400)
        assert cover.palette.hue_degrees == pytest.approx(231.0, abs=2.0)

    def test_load_keeps_track_order_and_missing_covers(self) -> None:
        response = httpx.Response(200, content=_jpeg((220, 30, 30)))
        server = _CoverServer(response)

        covers = _load(server, [None, _COVER_URL, None])

        assert covers[0] is None
        assert covers[1] is not None
        assert covers[2] is None

    def test_load_downloads_a_shared_album_cover_once(self) -> None:
        response = httpx.Response(200, content=_jpeg((220, 30, 30)))
        server = _CoverServer(response)

        covers = _load(server, [_COVER_URL, _COVER_URL])

        assert server.requested_urls == [_COVER_URL]
        assert covers[0] is not None
        assert covers[0] == covers[1]

    @pytest.mark.parametrize(
        "url",
        [
            "https://example.com/cover.jpg",
            "https://scdn.co.example.com/cover.jpg",
            "http://i.scdn.co/image/cover",
            "https://169.254.169.254/latest/meta-data",
        ],
    )
    def test_load_never_requests_urls_outside_spotify(self, url: str) -> None:
        response = httpx.Response(200, content=_jpeg((220, 30, 30)))
        server = _CoverServer(response)

        covers = _load(server, [url])

        assert covers == [None]
        assert server.requested_urls == []

    def test_load_skips_cover_when_download_fails(self) -> None:
        response = httpx.Response(404)
        server = _CoverServer(response)

        covers = _load(server, [_COVER_URL])

        assert covers == [None]
        assert server.requested_urls == [_COVER_URL]

    def test_load_skips_cover_that_is_not_an_image(self) -> None:
        response = httpx.Response(200, content=b"<html>not a cover</html>")
        server = _CoverServer(response)

        covers = _load(server, [_COVER_URL])

        assert covers == [None]
