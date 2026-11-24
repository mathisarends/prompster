from pathlib import Path
from uuid import uuid4

from harnessed import Inject, Plugin, SystemPrompt, ToolContext, hook, needs, tool
from harnessed.events import AssistantMessageEvent
from harnessed.hooks import Next, PrepareRequest
from harnessed.models import ModelRequest, UserMessage
from harnessed.sessions import SessionContext, SessionValue

from agent.deck.events import DECK_EVENTS, DeckChangedEvent
from agent.deck.params import (
    AddDeckTracksParams,
    RemoveDeckTracksParams,
    ReplaceDeckTracksParams,
)
from agent.deck.rendering import render_deck_state
from agent.deck.store import DeckStore
from agent.deck.views import DeckTrack, TrackReplacement
from agent.prompts import read_prompt
from agent.research import FoundTrack, TracksFoundEvent


class DeckPlugin(Plugin):
    """Edit the workspace deck and show its live state to the model.

    Tracks are added by URI. The plugin remembers every track research showed
    the model in a session value, so the catalog is saved with the conversation
    and URIs from earlier runs stay addable, also after compaction.
    """

    events = DECK_EVENTS
    session = needs(SessionContext)
    known_tracks = SessionValue(
        dict[str, FoundTrack], key="prompster.deck.known_tracks", default={}
    )

    def __init__(self, store: DeckStore) -> None:
        super().__init__()
        self._store = store

    def instructions(self) -> SystemPrompt:
        return SystemPrompt(read_prompt(Path(__file__).with_name("prompt.md")))

    @hook(PrepareRequest)
    async def append_deck_state(
        self,
        _event: PrepareRequest,
        next_: Next[ModelRequest],
    ) -> ModelRequest:
        request = await next_()
        state = render_deck_state(self._store.deck, max_tracks=self._store.max_tracks)
        return request.append_message(UserMessage(state))

    @hook(TracksFoundEvent)
    async def remember_tracks(self, event: TracksFoundEvent) -> None:
        def remember(known: dict[str, FoundTrack]) -> dict[str, FoundTrack]:
            fresh = {track.uri: track for track in event.tracks}
            kept = [(uri, track) for uri, track in known.items() if uri not in fresh]
            merged = [*kept, *fresh.items()]
            return dict(merged[-_MAX_KNOWN_TRACKS:])

        await self.known_tracks.update(remember)

    @hook(AssistantMessageEvent)
    async def settle_deck(self, event: AssistantMessageEvent) -> None:
        # The final reply ends the tool loop: the deck the user sees must be
        # consistent, whatever the model did on the way.
        if event.interrupted or event.message.tool_calls:
            return
        if (change := self._store.remove_duplicates()) is not None:
            await self.session.emit(change)

    @tool(
        description=(
            "Add tracks to the Hitster deck by Spotify URI. Creates the deck if "
            "needed and skips tracks already in it. Does not touch Spotify playlists."
        ),
        params=AddDeckTracksParams,
    )
    async def add_deck_tracks(
        self, params: AddDeckTracksParams, *, ctx: Inject[ToolContext]
    ) -> str:
        before = self._store.track_count
        tracks = [self._resolve(track.uri) for track in params.tracks]
        await self._publish(ctx, self._store.add(tracks))
        deck = self._store.deck
        assert deck is not None
        added = self._store.track_count - before
        requested = len(params.tracks)
        total = self._store.track_count
        if added == requested:
            return (
                f'Added {added} track(s) to Hitster deck "{deck.name}" ({total} total).'
            )
        message = (
            f"Added {added} of {requested} track(s) to Hitster deck "
            f'"{deck.name}" ({total} total).'
        )
        if self._store.is_full:
            return (
                f"{message} The deck is full (max {self._store.max_tracks}); "
                "extra tracks were skipped."
            )
        return f"{message} The others were already in the deck."

    @tool(
        description="Remove tracks from the Hitster deck by their deck track ID.",
        params=RemoveDeckTracksParams,
    )
    async def remove_deck_tracks(
        self, params: RemoveDeckTracksParams, *, ctx: Inject[ToolContext]
    ) -> str:
        track_ids = [str(track_id) for track_id in params.track_ids]
        await self._publish(ctx, self._store.remove(track_ids))
        return f"{len(track_ids)} track(s) removed from Hitster deck."

    @tool(
        description="Swap Hitster deck tracks for other tracks by Spotify URI.",
        params=ReplaceDeckTracksParams,
    )
    async def replace_deck_tracks(
        self, params: ReplaceDeckTracksParams, *, ctx: Inject[ToolContext]
    ) -> str:
        replacements = [
            TrackReplacement(
                track_id=str(replacement.old_id),
                track=self._resolve(replacement.new_uri),
            )
            for replacement in params.replacements
        ]
        await self._publish(ctx, self._store.replace(replacements))
        return f"{len(replacements)} track replacement(s) processed."

    def _resolve(self, uri: str) -> DeckTrack:
        found = self.known_tracks.get().get(uri)
        if found is None:
            raise ValueError(
                f"Unknown Spotify track URI: {uri}. Search for the song again."
            )
        return DeckTrack(
            id=str(uuid4()),
            title=found.title,
            artist=found.artist,
            year=found.year,
            spotify_uri=found.uri,
            cover_url=found.cover_url,
        )

    async def _publish(self, ctx: ToolContext, change: DeckChangedEvent | None) -> None:
        if change is not None:
            await ctx.emit(change)


# Bounds the catalog saved with the conversation; the oldest results go first.
_MAX_KNOWN_TRACKS = 600
