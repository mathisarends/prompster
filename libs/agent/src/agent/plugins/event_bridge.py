from collections.abc import Mapping
from typing import Any

from harnessed import Plugin, hook
from harnessed.events import AssistantMessageEvent as HarnessedAssistantMessageEvent
from harnessed.events import (
    CompactionAppliedEvent,
    TextDeltaEvent,
    ToolCallFinishedEvent,
    ToolCallRequestedEvent,
)
from harnessed.events import StepStartedEvent as HarnessedStepStartedEvent

from agent.events import (
    AssistantMessageChunkEvent,
    AssistantMessageEvent,
    ContextCompactedEvent,
    StepStartedEvent,
    ToolCallEvent,
    ToolCallSequenceStartedEvent,
    ToolResultEvent,
)
from agent.guardrails import PostRunGuardrails
from agent.plugins.labels import (
    ONBOARDING_TOOL,
    action_type,
    sequence_label,
    status_label,
)
from agent.plugins.run_context import AgentRunContext


class EventBridge(Plugin):
    """Translate harnessed session events into Prompster's public agent events."""

    def __init__(
        self,
        run: AgentRunContext,
        *,
        compaction_threshold: float = 0.8,
    ) -> None:
        super().__init__()
        self._run = run
        self._compaction_threshold = compaction_threshold
        self._guardrails = PostRunGuardrails(run.deck_store)

    @hook(HarnessedStepStartedEvent)
    def on_step_started(self, event: HarnessedStepStartedEvent) -> None:
        self._run.channel.publish(StepStartedEvent(step=event.step))

    @hook(TextDeltaEvent)
    def on_text_delta(self, event: TextDeltaEvent) -> None:
        if event.text:
            self._run.channel.publish(AssistantMessageChunkEvent(chunk=event.text))

    @hook(HarnessedAssistantMessageEvent)
    async def on_assistant_message(
        self,
        event: HarnessedAssistantMessageEvent,
    ) -> None:
        if event.interrupted:
            return
        message = event.message
        channel = self._run.channel
        if not message.tool_calls:
            # The tool loop has ended: settle the deck before the final reply.
            await self._guardrails.apply()
            self._run.publish_deck_updates()
            channel.publish(AssistantMessageEvent(content=message.content))
            return
        if message.content:
            channel.publish(AssistantMessageEvent(content=message.content))
        if any(call.name != ONBOARDING_TOOL for call in message.tool_calls):
            channel.publish(
                ToolCallSequenceStartedEvent(label=sequence_label(message.tool_calls))
            )

    @hook(ToolCallRequestedEvent)
    def on_tool_call_requested(self, event: ToolCallRequestedEvent) -> None:
        call = event.call
        if call.name == ONBOARDING_TOOL:
            return
        self._run.channel.publish(
            ToolCallEvent(
                tool_call_id=call.id,
                name=call.name,
                args=_plain_json(call.arguments),
                status_label=status_label(call),
                action_type=action_type(call.name),
            )
        )

    @hook(ToolCallFinishedEvent)
    def on_tool_call_finished(self, event: ToolCallFinishedEvent) -> None:
        call = event.call
        if call.name != ONBOARDING_TOOL:
            self._run.channel.publish(
                ToolResultEvent(
                    tool_call_id=call.id,
                    name=call.name,
                    result=event.result.text,
                    items=self._run.take_previews(call.id),
                )
            )
        self._run.publish_deck_updates()

    @hook(CompactionAppliedEvent)
    def on_compaction(self, event: CompactionAppliedEvent) -> None:
        # harnessed records no trigger. Below the threshold, only a provider
        # context-length error can have started this compaction.
        ratio = event.before_ratio
        is_reactive = ratio is not None and ratio < self._compaction_threshold
        self._run.channel.publish(
            ContextCompactedEvent(
                reason="reactive" if is_reactive else "proactive",
                tokens_before=event.before_tokens,
            )
        )


def _plain_json(value: Any) -> Any:
    """Copy harnessed's frozen tool arguments into plain JSON containers."""
    if isinstance(value, Mapping):
        return {key: _plain_json(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_plain_json(item) for item in value]
    return value
