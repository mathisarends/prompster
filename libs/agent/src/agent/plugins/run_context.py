import asyncio
from collections.abc import AsyncIterator, Iterable, Iterator
from contextlib import contextmanager

from harnessed.models import ToolCall
from spotifyify import RetryEvent

from agent.deck import DeckDraftUpdate, DeckStore
from agent.events import AgentEvent, DeckUpdatedEvent, ToolRetryEvent
from agent.tools import DeckCritic, Spotify
from agent.tools.retry_reporting import retry_sink
from agent.tools.views import ActionResultItem


class AgentEventChannel:
    """Unbounded FIFO from harnessed hooks to the agent's event stream."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[AgentEvent | None] = asyncio.Queue()

    async def __aiter__(self) -> AsyncIterator[AgentEvent]:
        while (event := await self._queue.get()) is not None:
            yield event

    def publish(self, event: AgentEvent) -> None:
        self._queue.put_nowait(event)

    def close(self) -> None:
        self._queue.put_nowait(None)


class AgentRunContext:
    """Resources shared by the plugins of one agent run."""

    def __init__(
        self,
        *,
        spotify: Spotify,
        deck_store: DeckStore,
        critic: DeckCritic,
        max_deck_tracks: int,
    ) -> None:
        self.spotify = spotify
        self.deck_store = deck_store
        self.critic = critic
        self.max_deck_tracks = max_deck_tracks
        self.channel = AgentEventChannel()
        self.suspended = False
        self._previews: dict[str, list[ActionResultItem]] = {}

    def set_previews(self, call_id: str, items: Iterable[ActionResultItem]) -> None:
        self._previews[call_id] = list(items)

    def take_previews(self, call_id: str) -> list[ActionResultItem]:
        return self._previews.pop(call_id, [])

    def publish_deck_updates(self) -> None:
        for update in self.deck_store.drain_deck_draft_updates():
            self.channel.publish(_deck_updated_event(update))

    @contextmanager
    def reporting_retries(self, call: ToolCall) -> Iterator[None]:
        def publish(retry: RetryEvent) -> None:
            self.channel.publish(
                ToolRetryEvent(
                    tool_call_id=call.id,
                    name=call.name,
                    attempt=retry.retry_number,
                    max_attempts=retry.max_retries,
                    retry_in_seconds=retry.retry_in_seconds,
                    status_code=retry.status_code,
                )
            )

        with retry_sink(publish):
            yield


def _deck_updated_event(update: DeckDraftUpdate) -> DeckUpdatedEvent:
    # Updates reference the live draft. The consumer reads them later, after
    # further tools may have changed it, so each event carries its own snapshot.
    snapshot = update.model_copy(deep=True)
    return DeckUpdatedEvent(deck_draft=snapshot.deck_draft, update=snapshot)
