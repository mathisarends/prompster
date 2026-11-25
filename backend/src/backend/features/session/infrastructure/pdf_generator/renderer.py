import asyncio
import io
import json
import shutil
import tempfile
from pathlib import Path

import qrcode
import qrcode.image.svg
import typst

from backend.features.session.application.ports import (
    PlaylistDeckGenerator,
    PlaylistDeckTrack,
)
from backend.features.session.infrastructure.pdf_generator.cover_art import (
    CoverArt,
    SpotifyCoverArtLoader,
)
from backend.features.session.infrastructure.pdf_generator.cover_palette import (
    CoverPalette,
)

_DECK_TEMPLATE = Path(__file__).parent / "deck.typ"
_FONT_DIRECTORY = Path(__file__).parent / "fonts"


class TypstPlaylistDeckGenerator(PlaylistDeckGenerator):
    def __init__(self, cover_art_loader: SpotifyCoverArtLoader) -> None:
        self._cover_art_loader = cover_art_loader

    async def generate(
        self,
        tracks: list[PlaylistDeckTrack],
        *,
        page_limit: int | None = None,
    ) -> bytes:
        cover_urls = [track.cover_url for track in tracks]
        covers = await self._cover_art_loader.load(cover_urls)
        return await asyncio.to_thread(_render_deck, tracks, covers, page_limit)


def _render_deck(
    tracks: list[PlaylistDeckTrack],
    covers: list[CoverArt | None],
    page_limit: int | None,
) -> bytes:
    with tempfile.TemporaryDirectory() as directory:
        workspace = Path(directory)
        songs = []
        for index, track in enumerate(tracks):
            song = _write_card_assets(workspace, index, track, covers[index])
            songs.append(song)

        deck_typ = workspace / "deck.typ"
        shutil.copy(_DECK_TEMPLATE, deck_typ)
        output = workspace / "deck.pdf"
        songs_json = json.dumps(songs, ensure_ascii=False)
        max_pages = "" if page_limit is None else str(page_limit)
        typst.compile(
            str(deck_typ),
            output=str(output),
            font_paths=[str(_FONT_DIRECTORY)],
            sys_inputs={"songs": songs_json, "max_pages": max_pages},
        )
        return output.read_bytes()


def _write_card_assets(
    workspace: Path,
    index: int,
    track: PlaylistDeckTrack,
    cover: CoverArt | None,
) -> dict[str, str | float | None]:
    qr_file = f"qr_{index}.svg"
    qr_svg = _make_qr_svg_bytes(track.spotify_url)
    (workspace / qr_file).write_bytes(qr_svg)

    cover_file = None
    year = int(track.release_year) if track.release_year.isdigit() else index
    palette = CoverPalette.for_year(year)
    if cover is not None:
        cover_file = f"cover_{index}.jpg"
        (workspace / cover_file).write_bytes(cover.jpeg)
        palette = cover.palette

    return {
        "title": track.title,
        "artist_names": track.artist_names,
        "release_year": track.release_year,
        "qr_file": qr_file,
        "cover_file": cover_file,
        "hue": palette.hue_degrees,
        "saturation": palette.saturation,
    }


def _make_qr_svg_bytes(spotify_url: str) -> bytes:
    image = qrcode.make(spotify_url, image_factory=qrcode.image.svg.SvgPathImage)
    buffer = io.BytesIO()
    image.save(buffer)
    return buffer.getvalue()
