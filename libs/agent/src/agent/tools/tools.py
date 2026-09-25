import json
import logging
from collections.abc import Callable
from typing import Any

from llm import ModelTool, ToolCall
from pydantic import BaseModel

from agent.deck import (
    DeckStore,
)
from agent.tools.di import Inject, ToolContext
from agent.tools.executor import ToolExecutor
from agent.tools.handler import DeckCritic, Spotify
from agent.tools.result_previews import (
    playlist_preview_items,
    track_preview_items,
)
from agent.tools.params import (
    AddDraftDeckTracksParams,
    AskOnboardingQuestionParams,
    PlaylistIdParams,
    RemoveDraftDeckTracksParams,
    ReplaceDraftDeckTracksParams,
    ReviewDeckParams,
    SearchParams,
)
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
        action_type: ActionType | None = None,
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

    def to_model_tools(self, phase: Phase | None = None) -> list[ModelTool]:
        tools = self._tools.values()
        if phase is not None:
            tools = [tool for tool in tools if tool.is_included_in(phase)]
        return [tool.to_model_tool() for tool in tools]

    def parse_args(self, call: ToolCall) -> dict[str, Any]:
        raw = call.arguments
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError as error:
            logger.error("Failed to parse tool args JSON: %s", error)
            return {}

    def parse_params(
        self, call: ToolCall, phase: Phase | None = None
    ) -> BaseModel | None:
        tool = self.get(call.name, phase=phase)
        if tool is None or tool.param_model is None:
            return None
        try:
            return tool.param_model.model_validate(self.parse_args(call))
        except Exception as error:
            logger.error("Failed to validate tool params: %s", error)
            return None

    def _register_default_tools(self) -> None:
        @self.action(
            description=("Stelle dem User eine einzelne Onboarding-Klärungsfrage. "),
            params=AskOnboardingQuestionParams,
            status_label=lambda params: params.status,
            action_type=ActionType.ASK_ONBOARDING_QUESTION,
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
                    hint=params.hint,
                    options=params.options,
                    recommended_option=params.recommended_option,
                    selection_mode=params.selection_mode,
                    is_last_question=params.is_last_question,
                ),
            )

        @self.action(
            params=SearchParams,
            status_label=lambda params: params.status_label("Tracks"),
            action_type=ActionType.SEARCH_TRACKS,
            included_in_phases={Phase.BUILD},
        )
        async def search_tracks(
            spotify: Inject[Spotify],
            store: Inject[DeckStore],
            params: SearchParams,
        ) -> ActionResult:
            try:
                tracks = await spotify.search_tracks(params)
                store.cache_tracks(tracks.tracks)
                return ActionResult.ok(
                    tracks.content,
                    items=track_preview_items(tracks.tracks),
                )
            except Exception as error:
                return ActionResult.fail(error)

        @self.action(
            params=SearchParams,
            status_label=lambda params: params.status_label("Playlists"),
            action_type=ActionType.SEARCH_PLAYLISTS,
            included_in_phases={Phase.BUILD},
        )
        async def search_playlists(
            spotify: Inject[Spotify],
            params: SearchParams,
        ) -> ActionResult:
            try:
                playlists = await spotify.search_playlists(params)
                return ActionResult.ok(
                    playlists.content,
                    items=playlist_preview_items(playlists.playlists),
                )
            except Exception as error:
                return ActionResult.fail(error)

        @self.action(
            description=(
                "Put Spotify track URI refs into the current Hitster deck. Creates "
                'a workspace deck named "Deck" when none exists, otherwise appends only tracks '
                "that are not already present by Spotify URI. This does not create "
                "or mutate a Spotify playlist."
            ),
            params=AddDraftDeckTracksParams,
            status_label=lambda params: params.status,
            action_type=ActionType.ADD_DECK_TRACKS,
            included_in_phases={Phase.BUILD},
        )
        async def add_deck_tracks(
            store: Inject[DeckStore],
            params: AddDraftDeckTracksParams,
        ) -> ActionResult:
            try:
                before = len(store.draft.tracks) if store.draft is not None else 0
                updated_deck = store.add_track_refs(params.tracks)
                added = len(updated_deck.tracks) - before
                requested = len(params.tracks)
                total = len(updated_deck.tracks)
                if added == requested:
                    return ActionResult.ok(
                        f"Added {added} track(s) to Hitster deck "
                        f'"{updated_deck.name}" ({total} total).'
                    )
                message = (
                    f"Added {added} of {requested} track(s) to Hitster deck "
                    f'"{updated_deck.name}" ({total} total).'
                )
                if store.is_full:
                    message += (
                        f" The deck is full (max {store.track_limit}); "
                        "extra tracks were skipped."
                    )
                else:
                    message += " The others were already in the deck."
                return ActionResult.ok(message)
            except Exception as error:
                return ActionResult.fail(error)

        @self.action(
            description=("Remove tracks from the current Hitster deck by ID."),
            params=RemoveDraftDeckTracksParams,
            status_label=lambda params: params.status,
            action_type=ActionType.REMOVE_DECK_TRACKS,
            included_in_phases={Phase.BUILD},
        )
        async def remove_deck_tracks(
            store: Inject[DeckStore],
            params: RemoveDraftDeckTracksParams,
        ) -> ActionResult:
            try:
                store.remove_tracks(params.track_ids)
                return ActionResult.ok(
                    f"{len(params.track_ids)} track(s) removed from Hitster deck."
                )
            except Exception as error:
                return ActionResult.fail(error)

        @self.action(
            description=("Replace tracks in the current Hitster deck by ID."),
            params=ReplaceDraftDeckTracksParams,
            status_label=lambda params: params.status,
            action_type=ActionType.REPLACE_DECK_TRACKS,
            included_in_phases={Phase.BUILD},
        )
        async def replace_deck_tracks(
            store: Inject[DeckStore],
            params: ReplaceDraftDeckTracksParams,
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
                "for research. Tracks are returned one page at a time (progressive "
                "discovery): start at offset=0 and only call again with the next "
                "offset (reported in the result) if you genuinely need more tracks. "
                "Do not try to pull an entire large playlist. The returned tracks are "
                "cached for later deck tools; this does not read or mutate the current "
                "workspace Hitster deck."
            ),
            params=PlaylistIdParams,
            status_label=lambda params: params.status_label(),
            action_type=ActionType.GET_SPOTIFY_PLAYLIST_TRACKS,
            included_in_phases={Phase.BUILD},
        )
        async def get_spotify_playlist_tracks(
            spotify: Inject[Spotify],
            store: Inject[DeckStore],
            params: PlaylistIdParams,
        ) -> ActionResult:
            try:
                playlist_tracks = await spotify.get_playlist_tracks(params)
                store.cache_tracks(playlist_tracks.tracks)
                return ActionResult.ok(
                    playlist_tracks.content,
                    items=track_preview_items(playlist_tracks.tracks),
                )
            except Exception as error:
                return ActionResult.fail(error)

        @self.action(
            description=(
                "Get critic feedback on the current Hitster deck near the end of a "
                "build loop. Returns concrete, structured suggestions you can act on "
                "with remove_deck_tracks/replace_deck_tracks/add_deck_tracks."
            ),
            params=ReviewDeckParams,
            status_label=lambda params: params.status,
            action_type=ActionType.SELF_REVIEW,
            included_in_phases={Phase.BUILD},
        )
        async def review_deck(
            critic: Inject[DeckCritic],
            params: ReviewDeckParams,
        ) -> ActionResult:
            try:
                result = await critic.review()
                return ActionResult.ok(result.content)
            except Exception as error:
                return ActionResult.fail(error)
