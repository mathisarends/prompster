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
    ActionType,
    ActionResult,
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
        action_type: ActionType = ActionType.FETCH,
        suspends_for_input: bool = False,
    ) -> Callable:
        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            self._register(
                Tool(
                    name=name or fn.__name__,
                    description=description,
                    fn=fn,
                    status_label=status_label,
                    action_type=action_type,
                    param_model=params,
                    suspends_for_input=suspends_for_input,
                )
            )
            return fn

        return decorator

    def _register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    async def execute(self, name: str, args: dict) -> ActionResult:
        return await self._executor.execute(name, args)

    def to_schema(self) -> list[ToolSchema]:
        return [t.to_schema() for t in self._tools.values()]

    def parse_args(self, call: ToolCall) -> dict[str, Any]:
        raw = call.function.arguments
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError as error:
            logger.error("Failed to parse tool args JSON: %s", error)
            return {}

    def serialize_result(self, result: ActionResult) -> str:
        if not isinstance(result, ActionResult):
            raise TypeError(f"Expected ActionResult, received {type(result).__name__}")
        return result.model_dump_json()

    def _register_default_tools(self) -> None:
        @self.action(
            description="",
            params=SearchParams,
            status_label=lambda params: params.status,
            action_type=ActionType.SEARCH,
        )
        async def search_tracks(
            spotify: Inject[Spotify],
            params: SearchParams,
        ) -> ActionResult:
            try:
                tracks = await spotify.search_tracks(params)
                return ActionResult.ok(tracks)
            except Exception as error:
                return ActionResult.fail(error)

        @self.action(
            description="",
            params=SearchParams,
            status_label=lambda params: params.status,
            action_type=ActionType.SEARCH,
        )
        async def search_albums(
            spotify: Inject[Spotify],
            params: SearchParams,
        ) -> ActionResult:
            try:
                albums = await spotify.search_albums(params)
                return ActionResult.ok(albums)
            except Exception as error:
                return ActionResult.fail(error)

        @self.action(
            description="",
            params=SearchParams,
            status_label=lambda params: params.status,
            action_type=ActionType.SEARCH,
        )
        async def search_playlists(
            spotify: Inject[Spotify],
            params: SearchParams,
        ) -> ActionResult:
            try:
                playlists = await spotify.search_playlists(params)
                return ActionResult.ok(playlists)
            except Exception as error:
                return ActionResult.fail(error)

        @self.action(
            description="",
            params=ArtistAlbumsParams,
            status_label=lambda params: params.status,
            action_type=ActionType.FETCH,
        )
        async def get_artist_albums(
            spotify: Inject[Spotify],
            params: ArtistAlbumsParams,
        ) -> ActionResult:
            try:
                artist_albums = await spotify.get_artist_albums(params)
                return ActionResult.ok(artist_albums)
            except Exception as error:
                return ActionResult.fail(error)

        @self.action(
            description="",
            params=ArtistTopTracksParams,
            status_label=lambda params: params.status,
            action_type=ActionType.FETCH,
        )
        async def get_artist_top_tracks(
            spotify: Inject[Spotify],
            params: ArtistTopTracksParams,
        ) -> ActionResult:
            try:
                top_tracks = await spotify.get_artist_top_tracks(params)
                return ActionResult.ok(top_tracks)
            except Exception as error:
                return ActionResult.fail(error)

        @self.action(
            description="",
            params=AlbumTracksParams,
            status_label=lambda params: params.status,
            action_type=ActionType.FETCH,
        )
        async def get_album_tracks(
            spotify: Inject[Spotify],
            params: AlbumTracksParams,
        ) -> ActionResult:
            try:
                album_tracks = await spotify.get_album_tracks(params)
                return ActionResult.ok(album_tracks)
            except Exception as error:
                return ActionResult.fail(error)

        @self.action(
            description=(
                "Create the initial Hitster playlist draft in the workspace. "
                "Use this only when no draft exists yet; do not create a Spotify playlist."
            ),
            params=BuildDraftPlaylistParams,
            status_label=lambda params: params.status,
            action_type=ActionType.MUTATE,
        )
        async def create_draft_playlist(
            workspace_store: Inject[WorkspaceStore],
            params: BuildDraftPlaylistParams,
        ) -> ActionResult:
            try:
                playlist_draft = PlaylistDraft(name=params.name, tracks=params.tracks)
                saved_playlist = workspace_store.save_playlist_draft(playlist_draft)
                return ActionResult.ok(saved_playlist)
            except Exception as error:
                return ActionResult.fail(error)

        @self.action(
            description=(
                "Build or fully replace the current Hitster playlist draft in the "
                "workspace. Prefer create_draft_playlist for the initial draft and "
                "the add/remove/replace tools for refinements. Pinned tracks must "
                "be preserved unchanged."
            ),
            params=BuildDraftPlaylistParams,
            status_label=lambda params: params.status,
            action_type=ActionType.MUTATE,
        )
        async def build_draft_playlist(
            workspace_store: Inject[WorkspaceStore],
            params: BuildDraftPlaylistParams,
        ) -> ActionResult:
            try:
                playlist_draft = PlaylistDraft(name=params.name, tracks=params.tracks)
                saved_playlist = workspace_store.save_playlist_draft(playlist_draft)
                return ActionResult.ok(saved_playlist)
            except Exception as error:
                return ActionResult.fail(error)

        @self.action(
            description="Add tracks to the current Hitster playlist draft.",
            params=AddDraftPlaylistTracksParams,
            status_label=lambda params: params.status,
            action_type=ActionType.MUTATE,
        )
        async def add_draft_playlist_tracks(
            workspace_store: Inject[WorkspaceStore],
            params: AddDraftPlaylistTracksParams,
        ) -> ActionResult:
            try:
                updated_playlist = workspace_store.add_tracks(params.tracks)
                return ActionResult.ok(updated_playlist)
            except Exception as error:
                return ActionResult.fail(error)

        @self.action(
            description=(
                "Remove tracks from the current Hitster playlist draft by ID. "
                "Pinned tracks cannot be removed."
            ),
            params=RemoveDraftPlaylistTracksParams,
            status_label=lambda params: params.status,
            action_type=ActionType.MUTATE,
        )
        async def remove_draft_playlist_tracks(
            workspace_store: Inject[WorkspaceStore],
            params: RemoveDraftPlaylistTracksParams,
        ) -> ActionResult:
            try:
                updated_playlist = workspace_store.remove_tracks(params.track_ids)
                return ActionResult.ok(updated_playlist)
            except Exception as error:
                return ActionResult.fail(error)

        @self.action(
            description=(
                "Replace tracks in the current Hitster playlist draft by ID. "
                "Pinned tracks cannot be replaced."
            ),
            params=ReplaceDraftPlaylistTracksParams,
            status_label=lambda params: params.status,
            action_type=ActionType.MUTATE,
        )
        async def replace_draft_playlist_tracks(
            workspace_store: Inject[WorkspaceStore],
            params: ReplaceDraftPlaylistTracksParams,
        ) -> ActionResult:
            try:
                updated_playlist = workspace_store.replace_tracks(params.replacements)
                return ActionResult.ok(updated_playlist)
            except Exception as error:
                return ActionResult.fail(error)

        @self.action(
            description="",
            params=PlaylistIdParams,
            status_label=lambda params: params.status,
            action_type=ActionType.FETCH,
        )
        async def get_playlist_tracks(
            spotify: Inject[Spotify],
            params: PlaylistIdParams,
        ) -> ActionResult:
            try:
                playlist_tracks = await spotify.get_playlist_tracks(params)
                return ActionResult.ok(playlist_tracks)
            except Exception as error:
                return ActionResult.fail(error)

        @self.action(
            description=(
                "Ask the user one or more clarifying questions before proceeding. "
                "Use this when the task is ambiguous and user input is required. "
                "Provide 1–4 questions, each with 1–4 selectable options. "
                "The user may also type a free-text answer or skip a question."
            ),
            params=AskFollowUpParams,
            status_label=lambda params: params.status,
            action_type=ActionType.INTERACT,
            suspends_for_input=True,
        )
        async def ask_follow_up(params: AskFollowUpParams) -> ActionResult:
            try:
                follow_up_payload = params.model_dump_json()
                return ActionResult.ok(follow_up_payload)
            except Exception as error:
                return ActionResult.fail(error)
