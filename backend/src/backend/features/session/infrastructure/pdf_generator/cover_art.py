import asyncio
import io
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx
from PIL import Image, UnidentifiedImageError

from backend.features.session.infrastructure.pdf_generator.cover_palette import (
    CoverPalette,
)

logger = logging.getLogger(__name__)

# Cover URLs come from Spotify's catalogue; anything else is not fetched.
_ALLOWED_HOSTS = ("scdn.co", "spotifycdn.com")
_DOWNLOAD_TIMEOUT_SECONDS = 5.0
_MAX_CONCURRENT_DOWNLOADS = 8
_MAX_COVER_BYTES = 5 * 1024 * 1024
# A cover prints about 2.4 cm wide, so 400 px stays above 400 dpi.
_PRINT_EDGE_PIXELS = 400
_JPEG_QUALITY = 88


@dataclass(frozen=True, slots=True)
class CoverArt:
    jpeg: bytes
    palette: CoverPalette


class SpotifyCoverArtLoader:
    """Downloads album covers for the printable deck; a failed cover is None."""

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport

    async def load(self, urls: Sequence[str | None]) -> list[CoverArt | None]:
        allowed = {url for url in urls if url is not None and _is_allowed(url)}
        wanted = sorted(allowed)
        slots = asyncio.Semaphore(_MAX_CONCURRENT_DOWNLOADS)
        async with httpx.AsyncClient(
            timeout=_DOWNLOAD_TIMEOUT_SECONDS, transport=self._transport
        ) as client:
            downloads = [_download(client, slots, url) for url in wanted]
            covers = await asyncio.gather(*downloads)
        cover_by_url: dict[str | None, CoverArt | None] = dict(
            zip(wanted, covers, strict=True)
        )
        return [cover_by_url.get(url) for url in urls]


def _is_allowed(url: str) -> bool:
    parts = urlsplit(url)
    host = parts.hostname or ""
    return parts.scheme == "https" and any(
        host == allowed or host.endswith(f".{allowed}") for allowed in _ALLOWED_HOSTS
    )


async def _download(
    client: httpx.AsyncClient, slots: asyncio.Semaphore, url: str
) -> CoverArt | None:
    try:
        async with slots:
            response = await client.get(url)
        response.raise_for_status()
    except httpx.HTTPError as error:
        logger.warning("Cover download failed for %s: %s", url, error)
        return None
    if len(response.content) > _MAX_COVER_BYTES:
        logger.warning("Cover at %s exceeds the size limit", url)
        return None
    return await asyncio.to_thread(_decode, response.content)


def _decode(data: bytes) -> CoverArt | None:
    try:
        with Image.open(io.BytesIO(data)) as source:
            image = source.convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        logger.warning("Cover could not be decoded: %s", error)
        return None
    image.thumbnail((_PRINT_EDGE_PIXELS, _PRINT_EDGE_PIXELS))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=_JPEG_QUALITY)
    palette = CoverPalette.from_image(image)
    return CoverArt(jpeg=buffer.getvalue(), palette=palette)
