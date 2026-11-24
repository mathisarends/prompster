from typing import Annotated, TypedDict
from uuid import UUID, uuid4

from harnessed import Inject, Plugin, SystemPrompt, ToolContext, hook, needs, tool
from harnessed.events import AssistantMessageEvent
from harnessed.hooks import Next, PrepareRequest
from harnessed.models import ModelRequest, UserMessage
from harnessed.sessions import SessionContext, SessionValue
from pydantic import Field

from agent.deck.events import DECK_EVENTS, DeckChangedEvent
from agent.deck.rendering import render_deck_state
from agent.deck.store import DeckStore
from agent.deck.views import DeckTrack, TrackReplacement
from agent.research import FoundTrack, TracksFoundEvent

TrackUri = Annotated[
    str,
    Field(
        pattern=r"^spotify:track:",
        description="Spotify track URI from search or playlist results.",
    ),
]


class TrackSwap(TypedDict):
    track_id: UUID
    uri: TrackUri


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
        return SystemPrompt(_INSTRUCTIONS)

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

    @tool
    async def add_deck_tracks(
        self,
        uris: Annotated[list[TrackUri], Field(min_length=1)],
        *,
        ctx: Inject[ToolContext],
    ) -> str:
        """Add tracks to the Hitster deck by Spotify URI.

        Creates the deck if needed and skips tracks already in it. Does not
        touch Spotify playlists.
        """
        before = self._store.track_count
        tracks = [self._resolve(uri) for uri in uris]
        await self._publish(ctx, self._store.add(tracks))
        deck = self._store.deck
        assert deck is not None
        added = self._store.track_count - before
        requested = len(uris)
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

    @tool
    async def remove_deck_tracks(
        self,
        track_ids: Annotated[
            list[UUID],
            Field(min_length=1, description="Track IDs from the current deck state."),
        ],
        *,
        ctx: Inject[ToolContext],
    ) -> str:
        """Remove tracks from the Hitster deck by their deck track ID."""
        removed = [str(track_id) for track_id in track_ids]
        await self._publish(ctx, self._store.remove(removed))
        return f"{len(removed)} track(s) removed from Hitster deck."

    @tool
    async def replace_deck_tracks(
        self,
        swaps: Annotated[
            list[TrackSwap],
            Field(
                min_length=1,
                description="Deck track IDs and the Spotify track URIs replacing them.",
            ),
        ],
        *,
        ctx: Inject[ToolContext],
    ) -> str:
        """Swap Hitster deck tracks for other tracks by Spotify URI."""
        replacements = [
            TrackReplacement(
                track_id=str(swap["track_id"]), track=self._resolve(swap["uri"])
            )
            for swap in swaps
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

_INSTRUCTIONS = """\
<deck_building>
The latest `<deck_state>` message is the source of truth for the current deck, including track IDs, remaining capacity, and year coverage. Never fetch or restate the deck to find out what is in it.

Building:
1. Finish researching and settle on the selection first. Do not add tracks piecemeal while still searching.
2. Write one short line saying what you built and what stands out, for example: "Hab dir einen Mix aus 80s-Synthpop, New Wave und ein paar vergessenen Talk-Talk-Cuts zusammengestellt."
3. Add the selection with `add_deck_tracks`, ideally in one call.
4. Fill the deck toward its capacity unless the user asked for fewer songs or the niche genuinely runs out.

Refining:
- Use the smallest fitting edit: `add_deck_tracks`, `remove_deck_tracks`, or `replace_deck_tracks`.
- If a URI is rejected as unknown, search for that song again and retry.
- A `<user_events>` block lists manual deck changes the user made right before that message. Treat them as deliberate and never undo them unless asked.

Tool labels:
- `status` is a short German present-tense label for the UI, specific to the action: "Baue das 80er-Deck", "Tausche zwei Synthpop-Tracks".
- When several calls form one work step, set `sequence_label` on the first call only: "Grabe Deutschrap-Kanten aus".
- Search and playlist tools show their query automatically, so they need no `status`.
</deck_building>"""
