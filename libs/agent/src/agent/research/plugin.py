from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from harnessed import Inject, Plugin, SystemPrompt, ToolContext, tool
from spotifyify import RetryEvent

from agent.prompts import read_prompt
from agent.research.events import (
    RESEARCH_EVENTS,
    PlaylistsFoundEvent,
    SpotifyRetryEvent,
    TracksFoundEvent,
)
from agent.research.params import PlaylistIdParams, SearchParams
from agent.research.spotify import Spotify


class ResearchPlugin(Plugin):
    """Read-only Spotify research. Independent searches run in parallel.

    Every result is also emitted as an event: the deck plugin remembers the
    tracks so their URIs stay addable, and the application shows previews.
    """

    events = RESEARCH_EVENTS

    def __init__(self, spotify: Spotify) -> None:
        super().__init__()
        self._spotify = spotify

    def instructions(self) -> SystemPrompt:
        return SystemPrompt(read_prompt(Path(__file__).with_name("prompt.md")))

    @tool(
        description=(
            "Search Spotify tracks. Results include each track's URI, artist, "
            "title, and release year."
        ),
        params=SearchParams,
        readonly=True,
        parallel=True,
    )
    async def search_tracks(
        self,
        params: SearchParams,
        *,
        ctx: Inject[ToolContext],
    ) -> str:
        with self._reporting_retries(ctx):
            result = await self._spotify.search_tracks(params)
        await ctx.emit(TracksFoundEvent(call_id=ctx.call.id, tracks=result.tracks))
        return result.content

    @tool(
        description=(
            "Search Spotify playlists to discover clusters of candidate tracks. "
            "Open promising ones with get_spotify_playlist_tracks."
        ),
        params=SearchParams,
        readonly=True,
        parallel=True,
    )
    async def search_playlists(
        self,
        params: SearchParams,
        *,
        ctx: Inject[ToolContext],
    ) -> str:
        with self._reporting_retries(ctx):
            result = await self._spotify.search_playlists(params)
        await ctx.emit(
            PlaylistsFoundEvent(call_id=ctx.call.id, playlists=result.playlists)
        )
        return result.content

    @tool(
        description=(
            "Read one page of an external Spotify playlist for research. Start at "
            "offset 0 and request the next offset from the result only if you need "
            "more tracks. Does not read or change the Hitster deck."
        ),
        params=PlaylistIdParams,
        readonly=True,
        parallel=True,
    )
    async def get_spotify_playlist_tracks(
        self,
        params: PlaylistIdParams,
        *,
        ctx: Inject[ToolContext],
    ) -> str:
        with self._reporting_retries(ctx):
            result = await self._spotify.get_playlist_tracks(params)
        await ctx.emit(TracksFoundEvent(call_id=ctx.call.id, tracks=result.tracks))
        return result.content

    @contextmanager
    def _reporting_retries(self, ctx: ToolContext) -> Iterator[None]:
        async def report(retry: RetryEvent) -> None:
            await ctx.emit(
                SpotifyRetryEvent(
                    call_id=ctx.call.id,
                    tool_name=ctx.call.name,
                    attempt=retry.retry_number,
                    max_attempts=retry.max_retries,
                    retry_in_seconds=retry.retry_in_seconds,
                    status_code=retry.status_code,
                )
            )

        with self._spotify.retrying(report):
            yield
