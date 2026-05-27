import json
from uuid import UUID

from agent import UserEvent
from agent.messages import render_user_message_content
from llmify.messages import (
    AssistantMessage as LLMAssistantMessage,
    Message as LLMMessage,
    ToolCall as LLMToolCall,
    ToolResultMessage as LLMToolResultMessage,
    UserMessage as LLMUserMessage,
)

from backend.features.session.domain import (
    AssistantMessage,
    CompletedCall,
    FailedCall,
    Session,
    ToolCall,
    ToolCallSequence,
    UserCurationEvent,
    UserMessage,
    UserMessageAttachment,
)


def build_agent_history(*, session: Session) -> list[LLMMessage]:
    bound_event_ids: set[UUID] = set()
    messages: list[LLMMessage] = []
    for entry in session.entries:
        if isinstance(entry, UserMessage):
            for event in entry.user_curation_events:
                bound_event_ids.add(event.id)
            messages.append(_to_user_message(entry))
        elif isinstance(entry, AssistantMessage):
            messages.append(LLMAssistantMessage(content=entry.content))
        elif isinstance(entry, ToolCallSequence):
            messages.extend(_to_tool_call_messages(entry))

    trailing_events = _to_trailing_user_events(
        session=session, bound_event_ids=bound_event_ids
    )
    if trailing_events:
        # No user message followed these manual changes yet (e.g. agent is resuming
        # after follow-up answers). Surface them in a synthetic UserMessage so the
        # LLM still sees the curation block in turn order.
        messages.append(
            LLMUserMessage(content=render_user_message_content("", trailing_events))
        )

    return messages


def _to_user_message(message: UserMessage) -> LLMUserMessage:
    return LLMUserMessage(
        content=render_user_message_content(
            _to_user_message_content(message),
            _to_user_events_for_message(message=message),
        )
    )


def _to_tool_call_messages(sequence: ToolCallSequence) -> list[LLMMessage]:
    messages: list[LLMMessage] = []
    for call in sequence.calls:
        messages.append(
            LLMAssistantMessage(content="", tool_calls=[_to_llm_tool_call(call)])
        )
        if isinstance(call, CompletedCall):
            messages.append(
                LLMToolResultMessage(tool_call_id=call.id, content=call.result)
            )
        elif isinstance(call, FailedCall):
            messages.append(
                LLMToolResultMessage(tool_call_id=call.id, content=call.error)
            )
    return messages


def _to_user_message_content(message: UserMessage) -> str:
    if not message.attachments:
        return message.content

    payload = {
        "attachment_references": [
            _to_attachment_payload(attachment) for attachment in message.attachments
        ]
    }
    attachment_context = json.dumps(payload, ensure_ascii=False)
    if message.content.strip():
        return f"{message.content}\n\n{attachment_context}"
    return attachment_context


def _to_attachment_payload(attachment: UserMessageAttachment) -> dict[str, str | None]:
    return {
        "kind": attachment.kind.value,
        "external_id": attachment.external_id,
        "title": attachment.title,
        "subtitle": attachment.subtitle,
        "image_url": attachment.image_url,
        "spotify_id": attachment.spotify_id,
    }


def _to_llm_tool_call(call: ToolCall) -> LLMToolCall:
    return LLMToolCall(
        id=call.id,
        function={
            "name": call.function.name,
            "arguments": json.dumps(call.function.arguments, ensure_ascii=False),
        },
    )


def _to_user_events_for_message(*, message: UserMessage) -> list[UserEvent]:
    # Render every bound curation event, including consumed ones. The domain
    # treats UserMessage.user_curation_events as a permanent record of that
    # turn's intent — the LLM should keep seeing those past actions on every
    # subsequent run. ``consumed`` only gates user-facing restoration.
    return [_to_user_event(event=event) for event in message.user_curation_events]


def _to_trailing_user_events(
    *, session: Session, bound_event_ids: set[UUID]
) -> list[UserEvent]:
    return [
        _to_user_event(event=event)
        for event in session.unconsumed_user_curation_events
        if event.id not in bound_event_ids
    ]


def _to_user_event(*, event: UserCurationEvent) -> UserEvent:
    return UserEvent(
        type=event.event_type.value,
        track_title=event.track_title,
        track_artist=event.track_artist,
        occurred_at=event.occurred_at,
    )
