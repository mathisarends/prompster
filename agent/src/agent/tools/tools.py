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
    CreateDraftPlaylistParams,
    PlaylistIdParams,
    RemoveDraftPlaylistTracksParams,
    ReplaceDraftPlaylistTracksParams,
    SearchParams,
)

from agent.playlist import (
    PlaylistDraft,
    PlaylistDraftOperationStatus,
    PlaylistDraftToolResult,
    PlaylistDraftStore,
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

    def provide(self, *dependencies: object) -> None:
        self._context.provide(*dependencies)

    def resolve[T](self, expected_type: type[T]) -> T | None:
        return self._context.resolve(expected_type)

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def action[P: BaseModel](
        self,
        description: str | None = None,
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

    def _draft_success(
        self,
        operation: str,
        playlist_draft: PlaylistDraft,
    ) -> ActionResult:
        return ActionResult.ok(
            PlaylistDraftToolResult(
                playlist_draft=playlist_draft,
                operations=[
                    PlaylistDraftOperationStatus(
                        operation=operation,
                        success=True,
                    )
                ],
            )
        )

    def _draft_failure(
        self,
        operation: str,
        store: PlaylistDraftStore,
        error: Exception,
    ) -> ActionResult:
        return ActionResult(
            success=False,
            extracted_content=PlaylistDraftToolResult(
                playlist_draft=store.playlist_draft,
                operations=[
                    PlaylistDraftOperationStatus(
                        operation=operation,
                        success=False,
                        reason=str(error),
                    )
                ],
            ),
            error=str(error),
        )

    def _register_default_tools(self) -> None:
        @self.action(
            params=SearchParams,
            status_label=lambda params: params.status,
            action_type=ActionType.SEARCH,
        )
        async def search_tracks(
            spotify: Inject[Spotify],
            store: Inject[PlaylistDraftStore],
            params: SearchParams,
        ) -> ActionResult:
            try:
                tracks = await spotify.search_tracks(params)
                store.cache_tracks(tracks.tracks)
                return ActionResult.ok(tracks.content)
            except Exception as error:
                return ActionResult.fail(error)

        @self.action(
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
            params=ArtistTopTracksParams,
            status_label=lambda params: params.status,
            action_type=ActionType.FETCH,
        )
        async def get_artist_top_tracks(
            spotify: Inject[Spotify],
            store: Inject[PlaylistDraftStore],
            params: ArtistTopTracksParams,
        ) -> ActionResult:
            try:
                top_tracks = await spotify.get_artist_top_tracks(params)
                store.cache_tracks(top_tracks.tracks)
                return ActionResult.ok(top_tracks.content)
            except Exception as error:
                return ActionResult.fail(error)

        @self.action(
            params=AlbumTracksParams,
            status_label=lambda params: params.status,
            action_type=ActionType.FETCH,
        )
        async def get_album_tracks(
            spotify: Inject[Spotify],
            store: Inject[PlaylistDraftStore],
            params: AlbumTracksParams,
        ) -> ActionResult:
            try:
                album_tracks = await spotify.get_album_tracks(params)
                store.cache_tracks(album_tracks.tracks)
                return ActionResult.ok(album_tracks.content)
            except Exception as error:
                return ActionResult.fail(error)

        @self.action(
            description=(
                "Create an empty Hitster playlist in the workspace. Use this "
                "before adding tracks incrementally; it fails if a playlist "
                "already exists."
            ),
            params=CreateDraftPlaylistParams,
            status_label=lambda params: params.status,
            action_type=ActionType.MUTATE,
        )
        async def create_playlist(
            store: Inject[PlaylistDraftStore],
            params: CreateDraftPlaylistParams,
        ) -> ActionResult:
            try:
                playlist = store.create_empty_playlist_draft(params.name)
                return self._draft_success("create_playlist", playlist)
            except Exception as error:
                return self._draft_failure(
                    "create_playlist",
                    store,
                    error,
                )

        @self.action(
            description=(
                "Put Spotify track URI refs into the Hitster playlist. Creates "
                "a playlist when none exists, otherwise appends only tracks that are "
                "not already present by Spotify URI."
            ),
            params=AddDraftPlaylistTracksParams,
            status_label=lambda params: params.status,
            action_type=ActionType.MUTATE,
        )
        async def add_playlist_tracks(
            store: Inject[PlaylistDraftStore],
            params: AddDraftPlaylistTracksParams,
        ) -> ActionResult:
            try:
                updated_playlist = store.add_track_refs(params.tracks)
                return self._draft_success(
                    "add_playlist_tracks",
                    updated_playlist,
                )
            except Exception as error:
                return self._draft_failure(
                    "add_playlist_tracks",
                    store,
                    error,
                )

        @self.action(
            description=(
                "Remove tracks from the current Hitster playlist by ID. "
                "Pinned tracks cannot be removed."
            ),
            params=RemoveDraftPlaylistTracksParams,
            status_label=lambda params: params.status,
            action_type=ActionType.MUTATE,
        )
        async def remove_playlist_tracks(
            store: Inject[PlaylistDraftStore],
            params: RemoveDraftPlaylistTracksParams,
        ) -> ActionResult:
            try:
                updated_playlist = store.remove_tracks(params.track_ids)
                return self._draft_success(
                    "remove_playlist_tracks",
                    updated_playlist,
                )
            except Exception as error:
                return self._draft_failure(
                    "remove_playlist_tracks",
                    store,
                    error,
                )

        @self.action(
            description=(
                "Replace tracks in the current Hitster playlist by ID. "
                "Pinned tracks cannot be replaced."
            ),
            params=ReplaceDraftPlaylistTracksParams,
            status_label=lambda params: params.status,
            action_type=ActionType.MUTATE,
        )
        async def replace_playlist_tracks(
            store: Inject[PlaylistDraftStore],
            params: ReplaceDraftPlaylistTracksParams,
        ) -> ActionResult:
            try:
                updated_playlist = store.replace_track_refs(params.replacements)
                return self._draft_success(
                    "replace_playlist_tracks",
                    updated_playlist,
                )
            except Exception as error:
                return self._draft_failure(
                    "replace_playlist_tracks",
                    store,
                    error,
                )

        @self.action(
            description=(
                "Fetch tracks from an external Spotify playlist by playlist ID or URI "
                "for research. The returned tracks are cached for later playlist tools; "
                "this does not read or mutate the current workspace playlist."
            ),
            params=PlaylistIdParams,
            status_label=lambda params: params.status,
            action_type=ActionType.FETCH,
        )
        async def get_spotify_playlist_tracks(
            spotify: Inject[Spotify],
            store: Inject[PlaylistDraftStore],
            params: PlaylistIdParams,
        ) -> ActionResult:
            try:
                playlist_tracks = await spotify.get_playlist_tracks(params)
                store.cache_tracks(playlist_tracks.tracks)
                return ActionResult.ok(playlist_tracks.content)
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
