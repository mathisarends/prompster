import json
import logging
from collections.abc import Callable
from typing import Any

from llmify.messages import ToolCall
from pydantic import BaseModel

from agent.playlist import (
    PlaylistDraftStore,
)
from agent.tools.di import Inject, ToolContext
from agent.tools.executor import ToolExecutor
from agent.tools.handler import Spotify
from agent.tools.params import (
    AddDraftPlaylistTracksParams,
    AskOnboardingQuestionParams,
    CreateDraftPlaylistParams,
    PlaylistIdParams,
    RemoveDraftPlaylistTracksParams,
    ReplaceDraftPlaylistTracksParams,
    SearchParams,
)
from agent.tools.schemas import ToolSchema
from agent.tools.views import (
    ActionResult,
    ActionType,
    InputRequest,
    Phase,
    Tool,
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

    def get(self, name: str, phase: Phase | None = None) -> Tool | None:
        tool = self._tools.get(name)
        if tool is None:
            return None
        if phase is not None and not tool.is_included_in(phase):
            return None
        return tool

    def action[P: BaseModel](
        self,
        description: str | None = None,
        name: str | None = None,
        *,
        params: type[P] | None = None,
        status_label: Callable[[P], str] | None = None,
        action_type: ActionType = ActionType.FETCH,
        included_in_phases: set[Phase] | None = None,
        is_onboarding_question: bool = False,
    ) -> Callable:
        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            self._register(
                Tool(
                    name=name or fn.__name__,
                    description=description,
                    fn=fn,
                    status_label=status_label,
                    action_type=action_type,
                    included_in_phases=included_in_phases,
                    is_onboarding_question=is_onboarding_question,
                    param_model=params,
                )
            )
            return fn

        return decorator

    def _register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    async def execute(
        self, name: str, args: dict, phase: Phase | None = None
    ) -> ActionResult:
        tool = self._tools.get(name)
        if phase is not None and tool is not None and not tool.is_included_in(phase):
            return ActionResult.fail(
                f"Tool '{name}' is not available in phase '{phase.value}'."
            )
        return await self._executor.execute(name, args)

    def to_schema(self, phase: Phase | None = None) -> list[ToolSchema]:
        tools = self._tools.values()
        if phase is not None:
            tools = [tool for tool in tools if tool.is_included_in(phase)]
        return [tool.to_schema() for tool in tools]

    def parse_args(self, call: ToolCall) -> dict[str, Any]:
        raw = call.function.arguments
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError as error:
            logger.error("Failed to parse tool args JSON: %s", error)
            return {}

    def _register_default_tools(self) -> None:
        @self.action(
            description=(
                "Stelle dem User eine einzelne Onboarding-Klärungsfrage. "
                "Gib immer 3-8 konkrete Auswahlmöglichkeiten mit. "
                "Nutze selection_mode=multi_select nur, wenn mehrere Antworten "
                "gleichzeitig sinnvoll sind. "
                "Markiere nur die letzte Onboarding-Frage mit is_last_question."
            ),
            params=AskOnboardingQuestionParams,
            status_label=lambda params: params.status,
            action_type=ActionType.INTERACT,
            included_in_phases={Phase.ONBOARDING},
            is_onboarding_question=True,
        )
        async def ask_onboarding_question(
            params: AskOnboardingQuestionParams,
        ) -> ActionResult:
            return ActionResult.ok(
                extracted_content=f"Frage gestellt: {params.question}",
                input_request=InputRequest(
                    question=params.question,
                    options=params.options,
                    selection_mode=params.selection_mode,
                    is_last_question=params.is_last_question,
                ),
            )

        @self.action(
            params=SearchParams,
            status_label=lambda params: params.status,
            action_type=ActionType.SEARCH,
            included_in_phases={Phase.BUILD},
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
            included_in_phases={Phase.BUILD},
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
            description=(
                "Create an empty Hitster playlist in the workspace. Use this "
                "before adding tracks incrementally; it fails if a playlist "
                "already exists."
            ),
            params=CreateDraftPlaylistParams,
            status_label=lambda params: params.status,
            action_type=ActionType.MUTATE,
            included_in_phases={Phase.BUILD},
        )
        async def create_playlist(
            store: Inject[PlaylistDraftStore],
            params: CreateDraftPlaylistParams,
        ) -> ActionResult:
            try:
                playlist = store.create_empty_playlist_draft(params.name)
                return ActionResult.ok(f'Playlist "{playlist.name}" created.')
            except Exception as error:
                return ActionResult.fail(error)

        @self.action(
            description=(
                "Put Spotify track URI refs into the Hitster playlist. Creates "
                "a playlist when none exists, otherwise appends only tracks that are "
                "not already present by Spotify URI."
            ),
            params=AddDraftPlaylistTracksParams,
            status_label=lambda params: params.status,
            action_type=ActionType.MUTATE,
            included_in_phases={Phase.BUILD},
        )
        async def add_playlist_tracks(
            store: Inject[PlaylistDraftStore],
            params: AddDraftPlaylistTracksParams,
        ) -> ActionResult:
            try:
                updated_playlist = store.add_track_refs(params.tracks)
                return ActionResult.ok(
                    f"{len(params.tracks)} track reference(s) processed for "
                    f'playlist "{updated_playlist.name}".'
                )
            except Exception as error:
                return ActionResult.fail(error)

        @self.action(
            description=(
                "Remove tracks from the current Hitster playlist by ID. "
                "Pinned tracks cannot be removed."
            ),
            params=RemoveDraftPlaylistTracksParams,
            status_label=lambda params: params.status,
            action_type=ActionType.MUTATE,
            included_in_phases={Phase.BUILD},
        )
        async def remove_playlist_tracks(
            store: Inject[PlaylistDraftStore],
            params: RemoveDraftPlaylistTracksParams,
        ) -> ActionResult:
            try:
                store.remove_tracks(params.track_ids)
                return ActionResult.ok(
                    f"{len(params.track_ids)} track(s) removed from playlist."
                )
            except Exception as error:
                return ActionResult.fail(error)

        @self.action(
            description=(
                "Replace tracks in the current Hitster playlist by ID. "
                "Pinned tracks cannot be replaced."
            ),
            params=ReplaceDraftPlaylistTracksParams,
            status_label=lambda params: params.status,
            action_type=ActionType.MUTATE,
            included_in_phases={Phase.BUILD},
        )
        async def replace_playlist_tracks(
            store: Inject[PlaylistDraftStore],
            params: ReplaceDraftPlaylistTracksParams,
        ) -> ActionResult:
            try:
                store.replace_track_refs(params.replacements)
                return ActionResult.ok(
                    f"{len(params.replacements)} track replacement(s) processed."
                )
            except Exception as error:
                return ActionResult.fail(error)

        @self.action(
            description=(
                "Fetch tracks from an external Spotify playlist by playlist ID or URI "
                "for research. The returned tracks are cached for later playlist tools; "
                "this does not read or mutate the current workspace playlist."
            ),
            params=PlaylistIdParams,
            status_label=lambda params: params.status,
            action_type=ActionType.FETCH,
            included_in_phases={Phase.BUILD},
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
