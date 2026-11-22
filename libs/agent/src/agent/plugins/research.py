from harnessed import Inject, Plugin, SystemPrompt, ToolContext, tool

from agent.messages import load_prompt
from agent.plugins.run_context import AgentRunContext
from agent.tools.params import PlaylistIdParams, SearchParams
from agent.tools.result_previews import playlist_preview_items, track_preview_items


class ResearchPlugin(Plugin):
    """Read-only Spotify research. Independent searches run in parallel."""

    def __init__(self, run: AgentRunContext) -> None:
        super().__init__()
        self._run = run

    def instructions(self) -> SystemPrompt:
        return SystemPrompt(load_prompt("research"))

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
        with self._run.reporting_retries(ctx.call):
            result = await self._run.spotify.search_tracks(params)
        self._run.deck_store.cache_tracks(result.tracks)
        self._run.set_previews(ctx.call.id, track_preview_items(result.tracks))
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
        with self._run.reporting_retries(ctx.call):
            result = await self._run.spotify.search_playlists(params)
        self._run.set_previews(ctx.call.id, playlist_preview_items(result.playlists))
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
        with self._run.reporting_retries(ctx.call):
            result = await self._run.spotify.get_playlist_tracks(params)
        self._run.deck_store.cache_tracks(result.tracks)
        self._run.set_previews(ctx.call.id, track_preview_items(result.tracks))
        return result.content
