import asyncio
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from types import SimpleNamespace
from typing import cast

from agent.tools.handler.spotify import Spotify
from agent.tools.params import AlbumTracksParams
from spotifyify import Spotifyify


class _HttpStub:
    async def open(self) -> None:
        return None


class _AlbumsStub:
    def __init__(self, client: "_RetryHookClient") -> None:
        self._client = client

    async def get(self, album_id: str) -> SimpleNamespace:
        assert self._client.hook is not None
        self._client.hook(
            SimpleNamespace(
                method=SimpleNamespace(value="GET"),
                path="/search",
                status_code=429,
                retry_in_seconds=2.0,
                retry_number=1,
                max_retries=3,
            )
        )
        return SimpleNamespace(images=[], release_date=None)

    async def tracks(
        self, album_id: str, *, limit: int, offset: int
    ) -> SimpleNamespace:
        return SimpleNamespace(items=[])


class _RetryHookClient:
    def __init__(self) -> None:
        self.hook = None
        self.http = _HttpStub()
        self.albums = _AlbumsStub(self)

    @contextmanager
    def retry_hook(self, hook) -> Iterator[None]:
        self.hook = hook
        yield
        self.hook = None


class TestSpotifyRetryLogging:
    def test_spotify_calls_log_retries_while_the_hook_is_active(self, caplog) -> None:
        client = _RetryHookClient()
        spotify = Spotify(client=cast(Spotifyify, client))

        with caplog.at_level(logging.WARNING, logger="agent.tools.handler.spotify"):
            asyncio.run(
                spotify.get_album_tracks(
                    AlbumTracksParams(album_id="album-1", status="Lade Album")
                )
            )

        assert client.hook is None
        assert "Retrying Spotify request" in caplog.text
        assert "path=/search" in caplog.text
        assert "status_code=429" in caplog.text
