import logging
from collections.abc import Callable
from typing import Any, overload

from pydantic import BaseModel

from agent.tools.di import Inject, ToolContext
from agent.tools.executor import ToolExecutor
from agent.tools.handler import Spotify
from agent.tools.schemas import ToolSchema
from agent.tools.views import Tool
from agent.views import (
    AlbumTracksParams,
    ArtistAlbumsParams,
    ArtistTopTracksParams,
    CreatePlaylistParams,
    PlaylistIdParams,
    PlaylistTracksMutationParams,
    SearchParams,
)

logger = logging.getLogger(__name__)


class Tools:
    def __init__(
        self,
        context: ToolContext | None = None,
    ) -> None:
        self._tools: dict[str, Tool] = {}
        self._context = context if context is not None else ToolContext()
        self._executor = ToolExecutor(self._tools, self._context)

        self._register_default_tools()

    def set_context(self, context: ToolContext) -> None:
        self._context = context
        self._executor.set_context(context)

    def get_context(self) -> ToolContext:
        return self._context

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    @overload
    def action[P: BaseModel](
        self,
        description: str,
        name: str | None = None,
        *,
        status: str | Callable[[P], str] | None = None,
        status_label: str | Callable[[P], str] | None = None,
        params: type[P],
    ) -> Callable: ...

    @overload
    def action(
        self,
        description: str,
        name: str | None = None,
        *,
        status: str | None = None,
        status_label: str | None = None,
        params: None = None,
    ) -> Callable: ...

    def action[P: BaseModel](
        self,
        description: str,
        name: str | None = None,
        status: str | Callable[[P], str] | None = None,
        status_label: str | Callable[[P], str] | None = None,
        params: type[P] | None = None,
    ) -> Callable:
        if status is not None and status_label is not None:
            raise ValueError("Use either 'status' or 'status_label', not both")

        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            self._register(
                Tool(
                    name=name or fn.__name__,
                    description=description,
                    fn=fn,
                    status=status,
                    status_label=status_label,
                    param_model=params,
                )
            )
            return fn

        return decorator

    def _register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    async def execute(self, name: str, args: dict) -> Any:
        return await self._executor.execute(name, args)

    def to_schema(self) -> list[ToolSchema]:
        return [t.to_schema() for t in self._tools.values()]

    def render_status(self, name: str, args: dict[str, Any]) -> str | None:
        tool = self.get(name)
        if tool is None:
            raise ValueError(f"Unknown tool '{name}'. Available: {list(self._tools)}")
        return tool.render_status(args)

    def _register_default_tools(self) -> None:
        @self.action(
            description="Search Spotify for tracks matching a query. Returns title, artist, year and URI for each result.",
            status_label=lambda params: f"Suche nach '{params.query}'",
            params=SearchParams,
        )
        async def search_tracks(spotify: Inject[Spotify], params: SearchParams) -> str:
            return await spotify.search_tracks(params)

        @self.action(
            description="Search Spotify for albums matching a query. Returns album name, artist, year, track count and URI.",
            status_label=lambda params: f"Alben suchen: '{params.query}'",
            params=SearchParams,
        )
        async def search_albums(spotify: Inject[Spotify], params: SearchParams) -> str:
            return await spotify.search_albums(params)

        @self.action(
            description="Search Spotify for public playlists matching a query. Returns playlist name, track count and ID.",
            status_label=lambda params: f"Playlists suchen: '{params.query}'",
            params=SearchParams,
        )
        async def search_playlists(
            spotify: Inject[Spotify],
            params: SearchParams,
        ) -> str:
            return await spotify.search_playlists(params)

        @self.action(
            description="Get albums by an artist (pass artist URI or ID). Returns album name, year, track count.",
            status_label="Künstler-Alben laden",
            params=ArtistAlbumsParams,
        )
        async def get_artist_albums(
            spotify: Inject[Spotify],
            params: ArtistAlbumsParams,
        ) -> str:
            return await spotify.get_artist_albums(params)

        @self.action(
            description="Get an artist's top tracks. Pass artist URI or ID. Returns title, artist, year and URI.",
            status_label="Top-Tracks laden",
            params=ArtistTopTracksParams,
        )
        async def get_artist_top_tracks(
            spotify: Inject[Spotify],
            params: ArtistTopTracksParams,
        ) -> str:
            return await spotify.get_artist_top_tracks(params)

        @self.action(
            description="Get all tracks of an album by album URI or ID. Returns title, artist, year and URI.",
            status_label="Album-Tracks laden",
            params=AlbumTracksParams,
        )
        async def get_album_tracks(
            spotify: Inject[Spotify],
            params: AlbumTracksParams,
        ) -> str:
            return await spotify.get_album_tracks(params)

        @self.action(
            description="Create a Spotify playlist for the current user. Returns the playlist ID and URL.",
            status_label=lambda params: f"Playlist erstellen: '{params.name}'",
            params=CreatePlaylistParams,
        )
        async def create_playlist(
            spotify: Inject[Spotify],
            params: CreatePlaylistParams,
        ) -> str:
            return await spotify.create_playlist(params)

        @self.action(
            description="Add tracks to an existing Spotify playlist by playlist ID and a list of Spotify track URIs.",
            status_label=lambda params: f"{len(params.track_uris)} Tracks hinzufügen",
            params=PlaylistTracksMutationParams,
        )
        async def add_tracks_to_playlist(
            spotify: Inject[Spotify],
            params: PlaylistTracksMutationParams,
        ) -> str:
            return await spotify.add_tracks_to_playlist(params)

        @self.action(
            description="Get all tracks of an existing Spotify playlist. Returns title, artist, year and URI per track.",
            status_label="Playlist-Tracks laden",
            params=PlaylistIdParams,
        )
        async def get_playlist_tracks(
            spotify: Inject[Spotify],
            params: PlaylistIdParams,
        ) -> str:
            return await spotify.get_playlist_tracks(params)

        @self.action(
            description="Remove specific tracks from a Spotify playlist by playlist ID and a list of track URIs.",
            status_label=lambda params: f"{len(params.track_uris)} Tracks entfernen",
            params=PlaylistTracksMutationParams,
        )
        async def remove_tracks_from_playlist(
            spotify: Inject[Spotify],
            params: PlaylistTracksMutationParams,
        ) -> str:
            return await spotify.remove_tracks_from_playlist(params)

        @self.action(
            description="Remove all tracks from a Spotify playlist (clear it completely).",
            status_label="Playlist leeren",
            params=PlaylistIdParams,
        )
        async def clear_playlist(
            spotify: Inject[Spotify],
            params: PlaylistIdParams,
        ) -> str:
            return await spotify.clear_playlist(params)
