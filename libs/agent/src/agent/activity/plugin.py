from harnessed import Plugin, hook, needs
from harnessed.events import AssistantMessageEvent, ToolCallRequestedEvent
from harnessed.plugins import CallEnvelope, EnvelopePosition, InvalidEnvelope
from harnessed.sessions import SessionContext

from agent.activity.events import ToolCallAnnouncedEvent
from agent.activity.labels import (
    SequenceLabel,
    StatusLabel,
    action_type,
    batch_label,
    needs_status_label,
    status_label,
)


class ToolActivityPlugin(Plugin):
    """Announce each tool call with the UI labels the model attached to it."""

    events = (ToolCallAnnouncedEvent,)
    session = needs(SessionContext)

    def __init__(self) -> None:
        super().__init__()
        self._batch_labels: dict[str, str | None] = {}

    @hook(AssistantMessageEvent)
    def remember_batch(self, event: AssistantMessageEvent) -> None:
        calls = event.message.tool_calls
        label = batch_label(calls)
        self._batch_labels.update((call.id, label) for call in calls)

    @hook(ToolCallRequestedEvent)
    async def announce(self, event: ToolCallRequestedEvent) -> None:
        call = event.call
        await self.session.emit(
            ToolCallAnnouncedEvent(
                call=call,
                status_label=status_label(call),
                batch_label=self._batch_labels.pop(call.id, None),
                action_type=action_type(call.name),
            )
        )


def tool_activity() -> list[Plugin]:
    """The label envelopes and the plugin that announces labelled calls.

    harnessed strips the envelopes before a tool runs, and a missing or invalid
    label never fails a call.
    """
    return [
        CallEnvelope(
            StatusLabel,
            select=needs_status_label,
            on_invalid=InvalidEnvelope.DROP,
            position=EnvelopePosition.TRAILING,
            name="status-label",
        ),
        CallEnvelope(
            SequenceLabel,
            on_invalid=InvalidEnvelope.DROP,
            position=EnvelopePosition.TRAILING,
            name="sequence-label",
        ),
        ToolActivityPlugin(),
    ]
