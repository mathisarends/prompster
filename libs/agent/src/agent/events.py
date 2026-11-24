from typing import get_args, get_origin

from harnessed.events import (
    CompactionAppliedEvent,
    CompactionFinishedEvent,
    CompactionStartedEvent,
    SessionStatusChangedEvent,
    TextDeltaEvent,
    ToolCallFinishedEvent,
)
from harnessed.events.completion import TurnResultEvent

from agent.activity import ToolCallAnnouncedEvent
from agent.conversation import AssistantRepliedEvent
from agent.deck import (
    DeckCreatedEvent,
    DeckTracksAddedEvent,
    DeckTracksRemovedEvent,
    DeckTracksReplacedEvent,
)
from agent.onboarding import QuestionAskedEvent
from agent.research import PlaylistsFoundEvent, SpotifyRetryEvent, TracksFoundEvent

type AgentEvent = (
    # Text: deltas while the model writes, then the finished message.
    TextDeltaEvent
    | AssistantRepliedEvent
    # Tools: announced with UI labels, then finished with their result.
    | ToolCallAnnouncedEvent
    | ToolCallFinishedEvent
    # Capabilities, emitted by their plugins.
    | TracksFoundEvent
    | PlaylistsFoundEvent
    | SpotifyRetryEvent
    | DeckCreatedEvent
    | DeckTracksAddedEvent
    | DeckTracksRemovedEvent
    | DeckTracksReplacedEvent
    | QuestionAskedEvent
    # Context compaction, from harnessed's built-in compactor.
    | CompactionStartedEvent
    | CompactionAppliedEvent
    | CompactionFinishedEvent
    # Run control: running, paused and idle, then how the turn ended.
    | SessionStatusChangedEvent
    | TurnResultEvent[None]
)
"""Everything ``Agent.stream`` yields, all of it straight from the harnessed stream."""


def _event_types() -> tuple[type, ...]:
    return tuple(get_origin(item) or item for item in get_args(AgentEvent.__value__))


AGENT_EVENT_TYPES = _event_types()
