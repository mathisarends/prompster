from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated

from harnessed import Inject, Plugin, SystemPrompt, ToolContext, tool
from pydantic import Field
from spotifyify import RetryEvent

from agent.research.events import (
    RESEARCH_EVENTS,
    PlaylistsFoundEvent,
    SpotifyRetryEvent,
    TracksFoundEvent,
)
from agent.research.spotify import Spotify

Query = Annotated[str, Field(description="Spotify search query.")]
Limit = Annotated[int, Field(ge=1, le=50, description="Maximum results.")]


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
        return SystemPrompt(_INSTRUCTIONS)

    @tool(readonly=True, parallel=True)
    async def search_tracks(
        self, query: Query, limit: Limit = 10, *, ctx: Inject[ToolContext]
    ) -> str:
        """Search Spotify tracks.

        Results include each track's URI, artist, title, and release year.
        """
        with self._reporting_retries(ctx):
            result = await self._spotify.search_tracks(query, limit=limit)
        await ctx.emit(TracksFoundEvent(call_id=ctx.call.id, tracks=result.tracks))
        return result.content

    @tool(readonly=True, parallel=True)
    async def search_playlists(
        self, query: Query, limit: Limit = 10, *, ctx: Inject[ToolContext]
    ) -> str:
        """Search Spotify playlists to discover clusters of candidate tracks.

        Open promising ones with get_spotify_playlist_tracks.
        """
        with self._reporting_retries(ctx):
            result = await self._spotify.search_playlists(query, limit=limit)
        await ctx.emit(
            PlaylistsFoundEvent(call_id=ctx.call.id, playlists=result.playlists)
        )
        return result.content

    @tool(readonly=True, parallel=True)
    async def get_spotify_playlist_tracks(
        self,
        playlist_id: Annotated[str, Field(description="Spotify playlist URI or ID.")],
        playlist_name: Annotated[
            str,
            Field(
                description=(
                    "Readable playlist name from the search result, shown in the "
                    "UI. Never the playlist ID."
                )
            ),
        ],
        offset: Annotated[
            int, Field(ge=0, description="Zero-based page offset. Start at 0.")
        ] = 0,
        *,
        ctx: Inject[ToolContext],
    ) -> str:
        """Read one page of an external Spotify playlist for research.

        Start at offset 0 and request the next offset from the result only if
        you need more tracks. Does not read or change the Hitster deck.
        """
        del playlist_name  # Only the activity label reads it.
        with self._reporting_retries(ctx):
            result = await self._spotify.get_playlist_tracks(playlist_id, offset=offset)
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


_INSTRUCTIONS = """\
<research>
Treat the confirmed onboarding answers and any attached Spotify references as the brief. If the user allowed breadth, use it deliberately with adjacent artists, related scenes, and plausible left-field picks while keeping the core idea recognizable. If they insisted on a strict niche, stay inside it.

Plan several distinct search angles before you search, and run independent searches together in one step.

- Playlists find clusters. Mix editorial, decade+genre, mood, occasion, and scene queries: "ultimate 90s hits", "80s new wave essentials", "french house classics", "This Is ABBA".
- Tracks verify and fill gaps. Use artist, genre+year, mood+decade, local-scene, and one-hit-wonder queries: "synthpop 1983", "grunge 1992", "deutsche schlager 70er", "one hit wonder 90s".
- Search neighboring genres explicitly. For "80s Pop", also try new wave, synthpop, sophisti-pop, and dance pop.
- Do not rerun a query with tiny wording changes, and do not settle for the first page of one search.
- Keep a few surprises in the pool: deep but playable cuts, one-hit wonders, era jumps that still fit.
- Watch the year spread while you research. If results cluster, search specifically for the missing years.

Track URIs from earlier results in this conversation stay addable, also after older results were summarized.
</research>"""
