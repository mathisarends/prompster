import json
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from agent import InputImage, UserCurationEventType, UserEvent

from backend.features.session.application.ports import MessageAttachmentStore
from backend.features.session.domain import (
    AssistantMessage,
    Session,
    UserCurationEvent,
    UserMessage,
    UserMessageAttachment,
)


@dataclass(frozen=True, slots=True)
class AgentInput:
    """What the agent reads for one run: the new user turn.

    The agent keeps the rest of the conversation in its checkpoint. Sessions
    from before checkpoints start it from ``transcript`` instead.
    """

    text: str
    images: tuple[InputImage, ...] = ()
    curation_events: tuple[UserEvent, ...] = ()
    transcript: str | None = None


class AgentInputBuilder:
    """Builds the agent input from the session's trailing user message."""

    def __init__(self, message_attachment_store: MessageAttachmentStore) -> None:
        self._message_attachment_store = message_attachment_store

    async def build(self, *, session: Session) -> AgentInput:
        entries = session.entries
        message = entries[-1] if entries else None
        if not isinstance(message, UserMessage):
            return AgentInput(
                text="",
                curation_events=self._unbound_events(session),
                transcript=_transcript(entries),
            )
        images = await self._images(message)
        return AgentInput(
            text=_text(message),
            images=images,
            curation_events=(
                *(_user_event(event) for event in message.user_curation_events),
                *self._unbound_events(session),
            ),
            transcript=_transcript(entries[:-1]),
        )

    async def _images(self, message: UserMessage) -> tuple[InputImage, ...]:
        images = []
        for attachment in message.image_attachments:
            data = await self._message_attachment_store.load_bytes(
                storage_key=attachment.storage_key
            )
            images.append(InputImage(media_type=attachment.content_type, data=data))
        return tuple(images)

    def _unbound_events(self, session: Session) -> tuple[UserEvent, ...]:
        # Manual deck changes that no user message has carried to the agent yet.
        bound: set[UUID] = set()
        for entry in session.entries:
            if isinstance(entry, UserMessage):
                bound.update(event.id for event in entry.user_curation_events)
        return tuple(
            _user_event(event)
            for event in session.unconsumed_user_curation_events
            if event.id not in bound
        )


def _text(message: UserMessage) -> str:
    if not message.attachments:
        return message.content
    references = json.dumps(
        {"attachment_references": [_reference(item) for item in message.attachments]},
        ensure_ascii=False,
    )
    if message.content.strip():
        return f"{message.content}\n\n{references}"
    return references


def _reference(attachment: UserMessageAttachment) -> dict[str, str | None]:
    return {
        "kind": attachment.kind.value,
        "external_id": attachment.external_id,
        "title": attachment.title,
        "subtitle": attachment.subtitle,
        "image_url": attachment.image_url,
        "spotify_id": attachment.spotify_id,
    }


def _user_event(event: UserCurationEvent) -> UserEvent:
    return UserEvent(
        type=UserCurationEventType(event.event_type.value),
        occurred_at=event.occurred_at,
        track_title=event.track_title,
        track_artist=event.track_artist,
    )


def _transcript(entries: Sequence[object]) -> str | None:
    lines: list[str] = []
    for entry in entries:
        if isinstance(entry, UserMessage) and entry.content.strip():
            lines.append(f"User: {entry.content}")
        elif isinstance(entry, AssistantMessage) and entry.content.strip():
            lines.append(f"Assistant: {entry.content}")
    if not lines:
        return None
    return "\n".join(
        [
            "<earlier_conversation>",
            "The conversation so far, before you kept its full history:",
            *lines,
            "</earlier_conversation>",
        ]
    )
