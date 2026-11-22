from harnessed import Plugin, SystemPrompt, hook, tool
from harnessed.hooks import Next, PrepareRequest
from harnessed.models import ModelRequest, UserMessage

from agent.messages import load_prompt, render_deck_state
from agent.plugins.run_context import AgentRunContext
from agent.tools.params import (
    AddDraftDeckTracksParams,
    RemoveDraftDeckTracksParams,
    ReplaceDraftDeckTracksParams,
)


class DeckPlugin(Plugin):
    """Edit the workspace deck and show its live state to the model."""

    def __init__(self, run: AgentRunContext) -> None:
        super().__init__()
        self._run = run

    def instructions(self) -> SystemPrompt:
        return SystemPrompt(load_prompt("deck"))

    @hook(PrepareRequest)
    async def append_deck_state(
        self,
        _event: PrepareRequest,
        next_: Next[ModelRequest],
    ) -> ModelRequest:
        request = await next_()
        state = render_deck_state(
            self._run.deck_store.draft,
            max_tracks=self._run.max_deck_tracks,
        )
        return request.append_message(UserMessage(state))

    @tool(
        description=(
            "Add tracks to the Hitster deck by Spotify URI. Creates the deck if "
            "needed and skips tracks already in it. Does not touch Spotify playlists."
        ),
        params=AddDraftDeckTracksParams,
    )
    async def add_deck_tracks(self, params: AddDraftDeckTracksParams) -> str:
        store = self._run.deck_store
        before = len(store.draft.tracks) if store.draft is not None else 0
        deck = store.add_track_refs(params.tracks)
        total = len(deck.tracks)
        added = total - before
        requested = len(params.tracks)
        if added == requested:
            return f'Added {added} track(s) to Hitster deck "{deck.name}" ({total} total).'
        message = (
            f"Added {added} of {requested} track(s) to Hitster deck "
            f'"{deck.name}" ({total} total).'
        )
        if store.is_full:
            return (
                f"{message} The deck is full (max {store.track_limit}); "
                "extra tracks were skipped."
            )
        return f"{message} The others were already in the deck."

    @tool(
        description="Remove tracks from the Hitster deck by their deck track ID.",
        params=RemoveDraftDeckTracksParams,
    )
    async def remove_deck_tracks(self, params: RemoveDraftDeckTracksParams) -> str:
        self._run.deck_store.remove_tracks(params.track_ids)
        return f"{len(params.track_ids)} track(s) removed from Hitster deck."

    @tool(
        description="Swap Hitster deck tracks for other tracks by Spotify URI.",
        params=ReplaceDraftDeckTracksParams,
    )
    async def replace_deck_tracks(self, params: ReplaceDraftDeckTracksParams) -> str:
        self._run.deck_store.replace_track_refs(params.replacements)
        return f"{len(params.replacements)} track replacement(s) processed."
