import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from uuid import uuid4

from llmify.messages import UserMessage as LLMUserMessage

from backend.features.session.application import SessionConversationService
from backend.features.session.application.ports.session_runner import (
    SessionRunner,
    SessionRunnerEvent,
)
from backend.features.session.domain import (
    Session,
    SessionRepository,
    UserCurationEvent,
    UserCurationEventType,
)
from backend.features.session.infrastructure.session_runner import (
    _to_history_messages,
)


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
    async def run(self, *, session: Session) -> AsyncIterator[SessionRunnerEvent]:
        if False:
            yield


class _NoOpQuotaService:
    async def consume(self, *, user_id):
        return None


class TestSessionRunnerHistoryRendering:
    """``_to_history_messages`` produces the exact LLM message sequence the
    agent will replay. Curation events bind to the user message they belong
    to and appear inline in its content — mirroring the domain model where
    ``UserMessage.user_curation_events`` is part of the user entity.
    """

    def test_bound_event_renders_inside_its_user_message(self) -> None:
        session = Session(title="Deck", entries=[], owner_id=uuid4())
        session.add_user_message("start")
        session.add_assistant_message("ok")
        session.add_track(
            title="Umbrella", artist="Rihanna", year=2007, is_pinned=False
        )
        session.add_user_message("mach weiter")

        history = _to_history_messages(session=session)

        user_messages = [m for m in history if isinstance(m, LLMUserMessage)]
        assert len(user_messages) == 2
        assert user_messages[0].content == "start"
        assert "<user_events>" in user_messages[1].content
        assert "track_added" in user_messages[1].content
        assert "Rihanna - Umbrella" in user_messages[1].content
        assert user_messages[1].content.endswith("mach weiter")

    def test_trailing_unbound_event_becomes_a_synthetic_user_message(self) -> None:
        # Curation event recorded without a following user message
        # (e.g. resuming after follow-up answers) gets a synthetic UserMessage
        # so the LLM still sees the manual change in turn order.
        event = UserCurationEvent(
            id=uuid4(),
            event_type=UserCurationEventType.TRACK_REMOVED,
            track_id=uuid4(),
            track_title="Umbrella",
            track_artist="Rihanna",
            track_year=2007,
            created_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        session = Session(
            title="Deck",
            entries=[],
            owner_id=uuid4(),
            user_curation_events=[event],
        )

        history = _to_history_messages(session=session)

        assert len(history) == 1
        assert isinstance(history[0], LLMUserMessage)
        assert history[0].content == (
            "<user_events>\n"
            '<event type="track_removed" at="2026-01-01T00:00:00+00:00">'
            "Rihanna - Umbrella</event>\n"
            "</user_events>"
        )

    def test_consumed_bound_events_are_not_resurfaced(self) -> None:
        # Events the agent has already acknowledged on a previous run are
        # marked consumed — they must not appear in the next history rebuild.
        session = Session(title="Deck", entries=[], owner_id=uuid4())
        session.add_user_message("start")
        session.add_track(
            title="Umbrella", artist="Rihanna", year=2007, is_pinned=False
        )
        session.add_user_message("weiter")
        for event in session.unconsumed_user_curation_events:
            event.mark_consumed()

        history = _to_history_messages(session=session)

        user_messages = [m for m in history if isinstance(m, LLMUserMessage)]
        assert all("<user_events>" not in m.content for m in user_messages)

    def test_session_without_curation_events_emits_plain_user_messages(self) -> None:
        session = Session(title="Deck", entries=[], owner_id=uuid4())
        session.add_user_message("hi")
        session.add_assistant_message("hey")

        history = _to_history_messages(session=session)

        user_messages = [m for m in history if isinstance(m, LLMUserMessage)]
        assert [m.content for m in user_messages] == ["hi"]


class TestSendMessageConsumesCurationEvents:
    def test_send_message_consumes_user_curation_events_after_runner(self) -> None:
        user_id = uuid4()
        event = UserCurationEvent(
            event_type=UserCurationEventType.TRACK_PINNED,
            track_id=uuid4(),
            track_title="Umbrella",
            track_artist="Rihanna",
        )
        session = Session(
            title="Deck",
            entries=[],
            owner_id=user_id,
            user_curation_events=[event],
        )
        repository = _SessionRepositoryStub(session=session)
        service = SessionConversationService(
            session_repository=repository,
            runner=_EmptyRunner(),
            user_message_rate_limit_service=_NoOpQuotaService(),
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
