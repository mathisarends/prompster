import asyncio
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from agent import InputImage, UserCurationEventType, UserEvent

from backend.features.session.application.ports import MessageAttachmentStore
from backend.features.session.domain import (
    ImageAttachment,
    Session,
    UserCurationEvent,
)
from backend.features.session.domain import (
    UserCurationEventType as DomainCurationEventType,
)
from backend.features.session.infrastructure.agent_input import (
    AgentInput,
    AgentInputBuilder,
)

_TEST_TIME = datetime(2024, 1, 1, tzinfo=UTC)


class _AttachmentStore:
    async def load_bytes(self, *, storage_key: str) -> bytes:
        assert storage_key == "photo"
        return b"image-data"


def _build(session: Session) -> AgentInput:
    store = cast(MessageAttachmentStore, _AttachmentStore())
    return asyncio.run(AgentInputBuilder(store).build(session=session))


def test_trailing_user_message_is_the_input_with_its_deck_changes() -> None:
    session = Session.create(title="Deck", owner_id=UUID(int=1))
    session.add_track(title="Umbrella", artist="Rihanna", year=2007)
    session.add_user_message("mach weiter")

    agent_input = _build(session)

    [event] = agent_input.curation_events
    assert agent_input.text == "mach weiter"
    assert event.type is UserCurationEventType.TRACK_ADDED
    assert event.label == "Rihanna - Umbrella"
    assert agent_input.transcript is None


def test_unbound_deck_changes_are_sent_without_a_message() -> None:
    occurred_at = datetime(2026, 1, 1, tzinfo=UTC)
    event = UserCurationEvent.restore(
        id=UUID(int=2),
        event_type=DomainCurationEventType.TRACK_REMOVED,
        track_id=UUID(int=3),
        track_title="Umbrella",
        track_artist="Rihanna",
        track_year=2007,
        created_at=occurred_at,
    )
    session = Session.restore(
        id=UUID(int=4),
        created_at=_TEST_TIME,
        title="Deck",
        entries=[],
        owner_id=UUID(int=5),
        user_curation_events=[event],
    )

    agent_input = _build(session)

    assert agent_input.text == ""
    assert agent_input.curation_events == (
        UserEvent(
            type=UserCurationEventType.TRACK_REMOVED,
            occurred_at=occurred_at,
            track_title="Umbrella",
            track_artist="Rihanna",
        ),
    )


def test_image_attachments_are_loaded_for_the_agent() -> None:
    session = Session.create(title="Vision", owner_id=UUID(int=6))
    session.add_user_message(
        "Was ist auf dem Bild?",
        image_attachments=[
            ImageAttachment.restore(
                id=UUID(int=7),
                created_at=_TEST_TIME,
                storage_key="photo",
                content_type="image/jpeg",
                file_name="photo.jpg",
                size_bytes=10,
            )
        ],
    )

    agent_input = _build(session)

    assert agent_input.images == (InputImage("image/jpeg", b"image-data"),)


def test_earlier_messages_become_a_transcript_for_sessions_without_a_checkpoint() -> (
    None
):
    session = Session.create(title="Deck", owner_id=UUID(int=8))
    session.add_user_message("Bau mir ein 80er-Deck")
    session.add_assistant_message("Klar, ich starte mit Klassikern.")
    session.add_user_message("Mach es tanzbarer")

    agent_input = _build(session)

    assert agent_input.text == "Mach es tanzbarer"
    assert agent_input.transcript == (
        "<earlier_conversation>\n"
        "The conversation so far, before you kept its full history:\n"
        "User: Bau mir ein 80er-Deck\n"
        "Assistant: Klar, ich starte mit Klassikern.\n"
        "</earlier_conversation>"
    )
