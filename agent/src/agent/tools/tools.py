import json
import logging
from collections.abc import Callable
from typing import Any

from llmify.messages import ToolCall
from pydantic import BaseModel

from agent.tools.di import Inject, ToolContext
from agent.tools.executor import ToolExecutor
from agent.tools.handler import Spotify
from agent.tools.schemas import ToolSchema
from agent.tools.views import (
    Tool,
    AddDraftPlaylistTracksParams,
    AlbumTracksParams,
    ArtistAlbumsParams,
    ArtistTopTracksParams,
    AskFollowUpParams,
    BuildDraftPlaylistParams,
    PlaylistIdParams,
    RemoveDraftPlaylistTracksParams,
    ReplaceDraftPlaylistTracksParams,
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

    def action[P: BaseModel](
        self,
        description: str,
        name: str | None = None,
        *,
        params: type[P] | None = None,
        status_label: Callable[[P], str] | None = None,
        suspends_for_input: bool = False,
    ) -> Callable:
        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            self._register(
                Tool(
                    name=name or fn.__name__,
                    description=description,
                    fn=fn,
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
            description="",
            params=SearchParams,
            status_label=lambda params: params.status,
        )
        async def search_tracks(spotify: Inject[Spotify], params: SearchParams) -> str:
            return await spotify.search_tracks(params)

        @self.action(
            description="",
            params=SearchParams,
            status_label=lambda params: params.status,
        )
        async def search_albums(spotify: Inject[Spotify], params: SearchParams) -> str:
            return await spotify.search_albums(params)

        @self.action(
            description="",
            params=SearchParams,
            status_label=lambda params: params.status,
        )
        async def search_playlists(
            spotify: Inject[Spotify],
            params: SearchParams,
        ) -> str:
            return await spotify.search_playlists(params)

        @self.action(
            description="",
            params=ArtistAlbumsParams,
            status_label=lambda params: params.status,
        )
        async def get_artist_albums(
            spotify: Inject[Spotify],
            params: ArtistAlbumsParams,
        ) -> str:
            return await spotify.get_artist_albums(params)

        @self.action(
            description="",
            params=ArtistTopTracksParams,
            status_label=lambda params: params.status,
        )
        async def get_artist_top_tracks(
            spotify: Inject[Spotify],
            params: ArtistTopTracksParams,
        ) -> str:
            return await spotify.get_artist_top_tracks(params)

        @self.action(
            description="",
            params=AlbumTracksParams,
            status_label=lambda params: params.status,
        )
        async def get_album_tracks(
            spotify: Inject[Spotify],
            params: AlbumTracksParams,
        ) -> str:
            return await spotify.get_album_tracks(params)

        @self.action(
            description=(
                "Create the initial Hitster playlist draft in the workspace. "
                "Use this only when no draft exists yet; do not create a Spotify playlist."
            ),
            params=BuildDraftPlaylistParams,
            status_label=lambda params: params.status,
        )
        async def create_draft_playlist(
            workspace_store: Inject[WorkspaceStore],
            params: BuildDraftPlaylistParams,
        ) -> PlaylistDraft:
            playlist_draft = PlaylistDraft(name=params.name, tracks=params.tracks)
            return workspace_store.save_playlist_draft(playlist_draft)

        @self.action(
            description=(
                "Build or fully replace the current Hitster playlist draft in the "
                "workspace. Prefer create_draft_playlist for the initial draft and "
                "the add/remove/replace tools for refinements. Locked tracks must "
                "be preserved unchanged."
            ),
            params=BuildDraftPlaylistParams,
            status_label=lambda params: params.status,
        )
        async def build_draft_playlist(
            workspace_store: Inject[WorkspaceStore],
            params: BuildDraftPlaylistParams,
        ) -> PlaylistDraft:
            playlist_draft = PlaylistDraft(name=params.name, tracks=params.tracks)
            return workspace_store.save_playlist_draft(playlist_draft)

        @self.action(
            description="Add tracks to the current Hitster playlist draft.",
            params=AddDraftPlaylistTracksParams,
            status_label=lambda params: params.status,
        )
        async def add_draft_playlist_tracks(
            workspace_store: Inject[WorkspaceStore],
            params: AddDraftPlaylistTracksParams,
        ) -> PlaylistDraft:
            return workspace_store.add_tracks(params.tracks)

        @self.action(
            description=(
                "Remove tracks from the current Hitster playlist draft by ID. "
                "Locked tracks cannot be removed."
            ),
            params=RemoveDraftPlaylistTracksParams,
            status_label=lambda params: params.status,
        )
        async def remove_draft_playlist_tracks(
            workspace_store: Inject[WorkspaceStore],
            params: RemoveDraftPlaylistTracksParams,
        ) -> PlaylistDraft:
            return workspace_store.remove_tracks(params.track_ids)

        @self.action(
            description=(
                "Replace tracks in the current Hitster playlist draft by ID. "
                "Locked tracks cannot be replaced."
            ),
            params=ReplaceDraftPlaylistTracksParams,
            status_label=lambda params: params.status,
        )
        async def replace_draft_playlist_tracks(
            workspace_store: Inject[WorkspaceStore],
            params: ReplaceDraftPlaylistTracksParams,
        ) -> PlaylistDraft:
            return workspace_store.replace_tracks(params.replacements)

        @self.action(
            description="",
            params=PlaylistIdParams,
            status_label=lambda params: params.status,
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
            params=AskFollowUpParams,
            status_label=lambda params: params.status,
            suspends_for_input=True,
        )
        async def ask_follow_up(params: AskFollowUpParams) -> str:
            return params.model_dump_json()
