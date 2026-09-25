import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timezone
from uuid import uuid4

from llmify.messages import (
    AssistantMessage as LLMAssistantMessage,
    UserMessage as LLMUserMessage,
)

from agent.tools.views import Phase as AgentPhase
from backend.features.session.application import SessionConversationService
from backend.features.session.application.ports import (
    MessageAttachmentStore,
    StoredAttachment,
)
from backend.features.session.application.ports.session_runner import (
    SessionRunner,
    SessionRunnerCancelled,
    SessionRunnerEvent,
)
from backend.features.session.application.ports.title_generator import (
    SessionTitleGenerator,
)
from backend.features.session.domain import (
    Phase,
    Session,
    SessionRepository,
    UserCurationEvent,
    UserCurationEventType,
)
from backend.features.session.infrastructure.agent_history import AgentHistoryBuilder
from backend.features.session.infrastructure.session_runner import _agent_phase_for


class _SessionRepositoryStub(SessionRepository):
    def __init__(self, session: Session) -> None:
        self.session = session
        self.save_count = 0

    async def get_by_id(self, session_id):
        return self.session

    async def save(self, *, session: Session) -> Session:
        self.save_count += 1
        self.session = session
        return session

    async def update(self, session_id, title):
        return self.session

    async def delete(self, session_id) -> None:
        return None


class _EmptyRunner(SessionRunner):
    async def run(
        self,
        *,
        session: Session,
        model_id: str | None = None,
    ) -> AsyncIterator[SessionRunnerEvent]:
        if False:
            yield


class _TitleGeneratorStub(SessionTitleGenerator):
    async def generate(self, initial_prompt: str) -> str:
        return "Deck"


class _CancelledRunner(SessionRunner):
    async def run(
        self,
        *,
        session: Session,
        model_id: str | None = None,
    ) -> AsyncIterator[SessionRunnerEvent]:
        yield SessionRunnerCancelled()


class _MessageAttachmentStoreStub(MessageAttachmentStore):
    async def save_stashed_image_attachment(
        self,
        *,
        user_id,
        attachment_id,
        file_name,
        content_type,
        content,
    ) -> StoredAttachment:
        return StoredAttachment(
            storage_key=f"users/{user_id}/stash/{attachment_id}.png",
            content_type=content_type,
            file_name=file_name,
            size_bytes=len(content),
        )

    async def promote_stashed_image_attachment(
        self,
        *,
        user_id,
        session_id,
        stash_storage_key: str,
    ) -> str:
        file_name = stash_storage_key.rsplit("/", 1)[-1]
        return f"users/{user_id}/chat/{session_id}/{file_name}"

    async def save_image_attachment(
        self,
        *,
        session_id,
        message_id,
        attachment_id,
        file_name,
        content_type,
        content,
    ) -> StoredAttachment:
        return StoredAttachment(
            storage_key=f"sessions/{session_id}/{attachment_id}",
            content_type=content_type,
            file_name=file_name,
            size_bytes=len(content),
        )

    async def save_uploaded_image_attachment(
        self,
        *,
        session_id,
        attachment_id,
        file_name,
        content_type,
        content,
    ) -> StoredAttachment:
        return StoredAttachment(
            storage_key=f"sessions/{session_id}/uploads/{attachment_id}.png",
            content_type=content_type,
            file_name=file_name,
            size_bytes=len(content),
        )

    async def exists(self, *, storage_key: str) -> bool:
        return True

    async def load_bytes(self, *, storage_key: str) -> bytes:
        return b""

    async def create_signed_url(
        self,
        *,
        storage_key: str,
        expires_in_seconds: int,
    ) -> str:
        return f"https://example.com/{storage_key}"

    async def delete_session_attachments(self, *, user_id, session_id) -> None:
        return None

    async def delete_user_attachments(self, *, user_id) -> None:
        return None

    async def delete_unreferenced_uploaded_image_attachments(
        self,
        *,
        session_id,
        referenced_storage_keys: set[str],
    ) -> None:
        return None


class TestAgentPhaseMapping:
    def test_agent_phase_uses_persisted_session_phase(self) -> None:
        session = Session.restore(
            id=uuid4(),
            created_at=datetime.now(UTC),
            title="Deck",
            entries=[],
            owner_id=uuid4(),
            phase=Phase.BUILD,
        )

        assert _agent_phase_for(session) == AgentPhase.BUILD


class TestSessionRunnerHistoryRendering:
    """``AgentHistoryBuilder.build`` produces the exact LLM message sequence the
    agent will replay. Curation events bind to the user message they belong
    to and appear inline in its content — mirroring the domain model where
    ``UserMessage.user_curation_events`` is part of the user entity.
    """

    def test_bound_event_renders_inside_its_user_message(self) -> None:
        session = Session.create(title="Deck", owner_id=uuid4())
        session.add_user_message("start")
        session.add_assistant_message("ok")
        session.add_track(title="Umbrella", artist="Rihanna", year=2007)
        session.add_user_message("mach weiter")

        history = asyncio.run(
            AgentHistoryBuilder(_MessageAttachmentStoreStub()).build(session=session)
        )

        user_messages = [m for m in history if isinstance(m, LLMUserMessage)]
        assert len(user_messages) == 2
        assert user_messages[0].content == "start"
        assert "<user_events>" in user_messages[1].content
        assert "track_added" in user_messages[1].content
        assert "Rihanna - Umbrella" in user_messages[1].content
        assert user_messages[1].content.endswith("mach weiter")

    def test_trailing_unbound_event_becomes_a_synthetic_user_message(self) -> None:
        # Curation event recorded without a following user message
        # gets a synthetic UserMessage
        # so the LLM still sees the manual change in turn order.
        event = UserCurationEvent.restore(
            id=uuid4(),
            event_type=UserCurationEventType.TRACK_REMOVED,
            track_id=uuid4(),
            track_title="Umbrella",
            track_artist="Rihanna",
            track_year=2007,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        session = Session.restore(
            id=uuid4(),
            created_at=datetime.now(UTC),
            title="Deck",
            entries=[],
            owner_id=uuid4(),
            user_curation_events=[event],
        )

        history = asyncio.run(
            AgentHistoryBuilder(_MessageAttachmentStoreStub()).build(session=session)
        )

        assert len(history) == 1
        assert isinstance(history[0], LLMUserMessage)
        assert history[0].content == (
            "<user_events>\n"
            '<event type="track_removed" at="2026-01-01T00:00:00+00:00">'
            "Rihanna - Umbrella</event>\n"
            "</user_events>"
        )

    def test_consumed_bound_events_stay_visible_in_history(self) -> None:
        # Past curation events must remain visible on every subsequent run —
        # they are a permanent record of the user's intent for that turn
        # (mirrors the domain coupling UserMessage <-> user_curation_events).
        # The ``consumed`` flag only gates user-facing restoration, not
        # history visibility.
        session = Session.create(title="Deck", owner_id=uuid4())
        session.add_user_message("start")
        session.add_track(title="Umbrella", artist="Rihanna", year=2007)
        session.add_user_message("weiter")
        for event in session.unconsumed_user_curation_events:
            event.mark_consumed()

        history = asyncio.run(
            AgentHistoryBuilder(_MessageAttachmentStoreStub()).build(session=session)
        )

        user_messages = [m for m in history if isinstance(m, LLMUserMessage)]
        assert "<user_events>" in user_messages[1].content
        assert "track_added" in user_messages[1].content

    def test_session_without_curation_events_emits_plain_user_messages(self) -> None:
        session = Session.create(title="Deck", owner_id=uuid4())
        session.add_user_message("hi")
        session.add_assistant_message("hey")

        history = asyncio.run(
            AgentHistoryBuilder(_MessageAttachmentStoreStub()).build(session=session)
        )

        user_messages = [m for m in history if isinstance(m, LLMUserMessage)]
        assert [m.content for m in user_messages] == ["hi"]

    def test_full_multi_turn_rendering_keeps_past_events_visible(self) -> None:
        """Golden output: a 5-turn history where the user added a track
        2 turns ago. The curation event lives inside its bound UserMessage
        and remains visible on every later run — exactly what the LLM sees.

        The session transcript built below maps 1:1 to the asserted
        ``expected`` list, so you can read this test as a spec of how the
        agent perceives a multi-turn conversation with manual user actions.
        """
        session = Session.create(title="Deck", owner_id=uuid4())

        # Turn 1 — user opens the deck, no manual changes yet.
        session.add_user_message("Bau mir ein 80er-Deck")
        session.add_assistant_message("Klar, ich starte mit ein paar Klassikern.")

        # Turn 2 — user adds a track BEFORE typing the next message.
        # The addition is recorded as a curation event and binds to turn-2's UserMessage.
        session.add_track(title="Take On Me", artist="a-ha", year=1985)
        session.add_user_message("der track bleibt, sonst gerne austauschen")
        session.add_assistant_message("Verstanden, a-ha bleibt drin.")

        # Turn 3 — plain conversation, no manual change.
        # The earlier curation event is now "2 turns ago" — it must still be visible.
        session.add_user_message("Mach es etwas tanzbarer")

        # Simulate that previous agent runs already consumed the curation event.
        # consumed=True must NOT hide it from history rendering.
        for event in session.user_curation_events:
            event.mark_consumed()

        history = asyncio.run(
            AgentHistoryBuilder(_MessageAttachmentStoreStub()).build(session=session)
        )

        # The event timestamp is generated at runtime — pull it out so
        # the golden output below stays deterministic.
        track_added_event = session.user_curation_events[0]
        track_added_iso = track_added_event.occurred_at.isoformat()

        expected = [
            LLMUserMessage(content="Bau mir ein 80er-Deck"),
            LLMAssistantMessage(content="Klar, ich starte mit ein paar Klassikern."),
            LLMUserMessage(
                content=(
                    "<user_events>\n"
                    f'<event type="track_added" at="{track_added_iso}">'
                    "a-ha - Take On Me</event>\n"
                    "</user_events>\n"
                    "\n"
                    "der track bleibt, sonst gerne austauschen"
                )
            ),
            LLMAssistantMessage(content="Verstanden, a-ha bleibt drin."),
            LLMUserMessage(content="Mach es etwas tanzbarer"),
        ]

        assert [type(m) for m in history] == [type(m) for m in expected]
        assert [m.content for m in history] == [m.content for m in expected]


class TestSendMessageConsumesCurationEvents:
    def test_send_message_consumes_user_curation_events_after_runner(self) -> None:
        user_id = uuid4()
        event = UserCurationEvent.create(
            event_type=UserCurationEventType.TRACK_ADDED,
            track_id=uuid4(),
            track_title="Umbrella",
            track_artist="Rihanna",
        )
        session = Session.restore(
            id=uuid4(),
            created_at=datetime.now(UTC),
            title="Deck",
            entries=[],
            owner_id=user_id,
            user_curation_events=[event],
        )
        repository = _SessionRepositoryStub(session=session)
        service = SessionConversationService(
            session_repository=repository,
            runner=_EmptyRunner(),
            message_attachment_store=_MessageAttachmentStoreStub(),
            title_generator=_TitleGeneratorStub(),
        )

        async def run() -> None:
            async for _ in service.send_message(
                session_id=session.id,
                user_id=user_id,
                content="weiter",
            ):
                pass

        asyncio.run(run())

        assert event.consumed is True

    def test_send_message_does_not_consume_user_curation_events_when_cancelled(
        self,
    ) -> None:
        user_id = uuid4()
        event = UserCurationEvent.create(
            event_type=UserCurationEventType.TRACK_ADDED,
            track_id=uuid4(),
            track_title="Umbrella",
            track_artist="Rihanna",
        )
        session = Session.restore(
            id=uuid4(),
            created_at=datetime.now(UTC),
            title="Deck",
            entries=[],
            owner_id=user_id,
            user_curation_events=[event],
        )
        repository = _SessionRepositoryStub(session=session)
        service = SessionConversationService(
            session_repository=repository,
            runner=_CancelledRunner(),
            message_attachment_store=_MessageAttachmentStoreStub(),
            title_generator=_TitleGeneratorStub(),
        )

        async def run() -> None:
            async for _ in service.send_message(
                session_id=session.id,
                user_id=user_id,
                content="weiter",
            ):
                pass

        asyncio.run(run())

        assert event.consumed is False
