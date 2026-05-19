import json
import logging
from collections.abc import Callable
from typing import Any, overload

from llmify.messages import ToolCall
from pydantic import BaseModel

from agent.tools.di import Inject, ToolContext
from agent.tools.executor import ToolExecutor
from agent.tools.handler import Spotify
from agent.tools.schemas import ToolSchema
from agent.tools.views import (
    Tool,
    AlbumTracksParams,
    ArtistAlbumsParams,
    ArtistTopTracksParams,
    AskFollowUpParams,
    BuildDraftPlaylistParams,
    PlaylistIdParams,
    SearchParams,
)

from agent.workspace import PlaylistDraft, WorkspaceStore

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
        suspends_for_input: bool = False,
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
        suspends_for_input: bool = False,
    ) -> Callable: ...

    def action[P: BaseModel](
        self,
        description: str,
        name: str | None = None,
        status: str | Callable[[P], str] | None = None,
        status_label: str | Callable[[P], str] | None = None,
        params: type[P] | None = None,
        suspends_for_input: bool = False,
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
                    suspends_for_input=suspends_for_input,
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

    @staticmethod
    def parse_args(call: ToolCall) -> dict[str, Any]:
        raw = call.function.arguments
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError as error:
            logger.error("Failed to parse tool args JSON: %s", error)
            return {}

    @staticmethod
    def serialize_result(result: Any) -> str:
        if isinstance(result, str):
            return result
        if hasattr(result, "model_dump_json"):
            return result.model_dump_json()
        return json.dumps(result, ensure_ascii=False, default=str)

    def _register_default_tools(self) -> None:
        @self.action(
            description="Search Spotify for tracks matching a query.",
            status_label=lambda params: f"Suche nach '{params.query}'",
            params=SearchParams,
        )
        async def search_tracks(spotify: Inject[Spotify], params: SearchParams) -> str:
            return await spotify.search_tracks(params)

        @self.action(
            description="Search Spotify for albums matching a query.",
            status_label=lambda params: f"Alben suchen: '{params.query}'",
            params=SearchParams,
        )
        async def search_albums(spotify: Inject[Spotify], params: SearchParams) -> str:
            return await spotify.search_albums(params)

        @self.action(
            description="Search Spotify for public playlists matching a query.",
            status_label=lambda params: f"Playlists suchen: '{params.query}'",
            params=SearchParams,
        )
        async def search_playlists(
            spotify: Inject[Spotify],
            params: SearchParams,
        ) -> str:
            return await spotify.search_playlists(params)

        @self.action(
            description="Get albums by an artist.",
            status_label="Künstler-Alben laden",
            params=ArtistAlbumsParams,
        )
        async def get_artist_albums(
            spotify: Inject[Spotify],
            params: ArtistAlbumsParams,
        ) -> str:
            return await spotify.get_artist_albums(params)

        @self.action(
            description="Get an artist's top tracks.",
            status_label="Top-Tracks laden",
            params=ArtistTopTracksParams,
        )
        async def get_artist_top_tracks(
            spotify: Inject[Spotify],
            params: ArtistTopTracksParams,
        ) -> str:
            return await spotify.get_artist_top_tracks(params)

        @self.action(
            description="Get all tracks of an album.",
            status_label="Album-Tracks laden",
            params=AlbumTracksParams,
        )
        async def get_album_tracks(
            spotify: Inject[Spotify],
            params: AlbumTracksParams,
        ) -> str:
            return await spotify.get_album_tracks(params)

        @self.action(
            description=(
                "Build or replace the current Hitster playlist draft in the workspace. "
                "Use this after researching tracks; do not create a Spotify playlist."
            ),
            status_label=lambda params: f"Playlist-Entwurf bauen: '{params.name}'",
            params=BuildDraftPlaylistParams,
        )
        async def build_draft_playlist(
            workspace_store: Inject[WorkspaceStore],
            params: BuildDraftPlaylistParams,
        ) -> PlaylistDraft:
            playlist_draft = PlaylistDraft(name=params.name, tracks=params.tracks)
            return workspace_store.save_playlist_draft(playlist_draft)

        @self.action(
            description="Get all tracks of a Spotify playlist.",
            status_label="Playlist-Tracks laden",
            params=PlaylistIdParams,
        )
        async def get_playlist_tracks(
            spotify: Inject[Spotify],
            params: PlaylistIdParams,
        ) -> str:
            return await spotify.get_playlist_tracks(params)

        @self.action(
            description=(
                "Ask the user one or more clarifying questions before proceeding. "
                "Use this when the task is ambiguous and user input is required. "
                "Provide 1–4 questions, each with 1–4 selectable options. "
                "The user may also type a free-text answer or skip a question."
            ),
            status_label="Rückfragen stellen",
            params=AskFollowUpParams,
            suspends_for_input=True,
        )
        async def ask_follow_up(params: AskFollowUpParams) -> str:
            return params.model_dump_json()
