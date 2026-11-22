import base64
import json
from uuid import UUID

from agent import UserEvent
from agent.messages import render_user_message_content
from harnessed.models import AssistantMessage as LLMAssistantMessage
from harnessed.models import ImagePart, TextPart, ToolStatus
from harnessed.models import Message as LLMMessage
from harnessed.models import ToolCall as LLMToolCall
from harnessed.models import ToolMessage as LLMToolMessage
from harnessed.models import UserMessage as LLMUserMessage

from backend.features.session.application.ports import MessageAttachmentStore
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


class AgentHistoryBuilder:
    """Builds the ``history`` argument passed to the ``Agent``.

    Stateless: a single instance is safe to share. Translates the session's
    domain entries into the LLM message sequence that the agent will replay
    on every run.
    """

    def __init__(self, message_attachment_store: MessageAttachmentStore) -> None:
        self._message_attachment_store = message_attachment_store

    async def build(self, *, session: Session) -> list[LLMMessage]:
        bound_event_ids: set[UUID] = set()
        messages: list[LLMMessage] = []
        for entry in session.entries:
            match entry:
                case UserMessage():
                    for event in entry.user_curation_events:
                        bound_event_ids.add(event.id)
                    user_message = await self._to_user_message(entry)
                    messages.append(user_message)
                case AssistantMessage():
                    messages.append(LLMAssistantMessage(entry.content))
                case ToolCallSequence():
                    messages.extend(self._to_tool_call_messages(entry))

        trailing_events = self._to_trailing_user_events(
            session=session, bound_event_ids=bound_event_ids
        )
        if trailing_events:
            # No user message followed these manual changes yet. Surface them
            # in a synthetic UserMessage so the LLM sees the curation block.
            messages.append(
                LLMUserMessage(render_user_message_content("", trailing_events))
            )

        return messages

    async def _to_user_message(self, message: UserMessage) -> LLMUserMessage:
        rendered_text = render_user_message_content(
            self._to_user_message_content(message),
            self._to_user_events_for_message(message=message),
        )
        if not message.image_attachments:
            return LLMUserMessage(rendered_text)

        images = []
        for attachment in message.image_attachments:
            data = await self._message_attachment_store.load_bytes(
                storage_key=attachment.storage_key
            )
            encoded = base64.b64encode(data).decode("ascii")
            images.append(
                ImagePart(f"data:{attachment.content_type};base64,{encoded}")
            )
        return LLMUserMessage((TextPart(rendered_text or " "), *images))

    def _to_tool_call_messages(self, sequence: ToolCallSequence) -> list[LLMMessage]:
        messages: list[LLMMessage] = []
        for call in sequence.calls:
            messages.append(LLMAssistantMessage("", (self._to_llm_tool_call(call),)))
            if isinstance(call, CompletedCall):
                messages.append(LLMToolMessage(call.result, tool_call_id=call.id))
            elif isinstance(call, FailedCall):
                messages.append(
                    LLMToolMessage(
                        call.error,
                        tool_call_id=call.id,
                        status=ToolStatus.ERROR,
                    )
                )
        return messages

    def _to_user_message_content(self, message: UserMessage) -> str:
        if not message.attachments:
            return message.content

        payload = {
            "attachment_references": [
                self._to_attachment_payload(attachment)
                for attachment in message.attachments
            ]
        }
        attachment_context = json.dumps(payload, ensure_ascii=False)
        if message.content.strip():
            return f"{message.content}\n\n{attachment_context}"
        return attachment_context

    def _to_attachment_payload(
        self, attachment: UserMessageAttachment
    ) -> dict[str, str | None]:
        return {
            "kind": attachment.kind.value,
            "external_id": attachment.external_id,
            "title": attachment.title,
            "subtitle": attachment.subtitle,
            "image_url": attachment.image_url,
            "spotify_id": attachment.spotify_id,
        }

    def _to_llm_tool_call(self, call: ToolCall) -> LLMToolCall:
        return LLMToolCall(
            call.function.name,
            dict(call.function.arguments),
            id=call.id,
        )

    def _to_user_events_for_message(self, *, message: UserMessage) -> list[UserEvent]:
        # Render every bound curation event, including consumed ones. The domain
        # treats UserMessage.user_curation_events as a permanent record of that
        # turn's intent — the LLM should keep seeing those past actions on every
        # subsequent run. ``consumed`` only gates user-facing restoration.
        return [
            self._to_user_event(event=event) for event in message.user_curation_events
        ]

    def _to_trailing_user_events(
        self, *, session: Session, bound_event_ids: set[UUID]
    ) -> list[UserEvent]:
        return [
            self._to_user_event(event=event)
            for event in session.unconsumed_user_curation_events
            if event.id not in bound_event_ids
        ]

    def _to_user_event(self, *, event: UserCurationEvent) -> UserEvent:
        return UserEvent(
            type=event.event_type.value,
            track_title=event.track_title,
            track_artist=event.track_artist,
            occurred_at=event.occurred_at,
        )
