from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

from harnessed import Plugin, hook, needs
from harnessed.events import AssistantMessageEvent, TransientEvent
from harnessed.sessions import SessionContext


class ReplyEventKind(StrEnum):
    ASSISTANT_REPLIED = "conversation.assistant.replied"


@dataclass(frozen=True, slots=True)
class AssistantRepliedEvent(TransientEvent):
    """The complete text of one assistant message, after its text deltas.

    ``final`` marks the answer that ends the tool loop; other replies are the
    model's comments between tool calls.
    """

    message_id: str
    text: str
    final: bool
    type: Literal[ReplyEventKind.ASSISTANT_REPLIED] = field(
        default=ReplyEventKind.ASSISTANT_REPLIED, kw_only=True
    )


class ReplyPlugin(Plugin):
    """Put finished assistant messages on the stream, which carries only deltas."""

    events = (AssistantRepliedEvent,)
    session = needs(SessionContext)

    @hook(AssistantMessageEvent)
    async def publish_reply(self, event: AssistantMessageEvent) -> None:
        message = event.message
        if event.interrupted or not message.content:
            return
        await self.session.emit(
            AssistantRepliedEvent(
                message_id=message.id,
                text=message.content,
                final=not message.tool_calls,
            )
        )
