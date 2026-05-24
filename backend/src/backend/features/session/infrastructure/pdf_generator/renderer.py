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


class TypstPlaylistDeckGenerator(PlaylistDeckGenerator):
    _DECK_TEMPLATE = Path(__file__).parent / "deck.typ"

    async def generate(
        self,
        tracks: list[PlaylistDeckTrack],
        *,
        page_limit: int | None = None,
    ) -> bytes:
        loop = asyncio.get_running_loop()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output = tmp_path / "deck.pdf"

            songs_data = []
            for index, track in enumerate(tracks):
                qr_file = f"qr_{index}.svg"
                (tmp_path / qr_file).write_bytes(
                    self._make_qr_svg_bytes(track.spotify_url)
                )
                songs_data.append(
                    {
                        "title": track.title,
                        "artist_names": track.artist_names,
                        "release_year": track.release_year,
                        "qr_file": qr_file,
                    }
                )

            deck_typ = tmp_path / "deck.typ"
            shutil.copy(self._DECK_TEMPLATE, deck_typ)

            songs_json = json.dumps(songs_data, ensure_ascii=False)
            max_pages = "" if page_limit is None else str(page_limit)
            await loop.run_in_executor(
                None,
                lambda: typst.compile(
                    str(deck_typ),
                    output=str(output),
                    sys_inputs={"songs": songs_json, "max_pages": max_pages},
                ),
            )

            return output.read_bytes()

    def _make_qr_svg_bytes(self, spotify_url: str) -> bytes:
        image = qrcode.make(spotify_url, image_factory=qrcode.image.svg.SvgPathImage)
        buffer = io.BytesIO()
        image.save(buffer)
        return buffer.getvalue()
