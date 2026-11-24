from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

from harnessed.events import TransientEvent
from harnessed.models import ToolCall

from agent.activity.labels import ActionType


class ActivityEventKind(StrEnum):
    TOOL_CALL_ANNOUNCED = "activity.tool_call.announced"


@dataclass(frozen=True, slots=True)
class ToolCallAnnouncedEvent(TransientEvent):
    """A tool call the UI shows, with the labels the model gave it.

    It follows harnessed's ``ToolCallRequestedEvent`` for the same call; its
    ``ToolCallFinishedEvent`` resolves it.
    """

    call: ToolCall
    status_label: str | None = None
    batch_label: str | None = None
    action_type: ActionType | None = None
    type: Literal[ActivityEventKind.TOOL_CALL_ANNOUNCED] = field(
        default=ActivityEventKind.TOOL_CALL_ANNOUNCED, kw_only=True
    )
