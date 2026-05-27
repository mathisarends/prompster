import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from uuid import uuid4

from llmify.messages import (
    AssistantMessage as LLMAssistantMessage,
    UserMessage as LLMUserMessage,
)

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
from backend.features.session.infrastructure.agent_history import (
    build_agent_history,
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
    """``build_agent_history`` produces the exact LLM message sequence the
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

        history = build_agent_history(session=session)

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

        history = build_agent_history(session=session)

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
        session = Session(title="Deck", entries=[], owner_id=uuid4())
        session.add_user_message("start")
        session.add_track(
            title="Umbrella", artist="Rihanna", year=2007, is_pinned=False
        )
        session.add_user_message("weiter")
        for event in session.unconsumed_user_curation_events:
            event.mark_consumed()

        history = build_agent_history(session=session)

        user_messages = [m for m in history if isinstance(m, LLMUserMessage)]
        assert "<user_events>" in user_messages[1].content
        assert "track_added" in user_messages[1].content

    def test_session_without_curation_events_emits_plain_user_messages(self) -> None:
        session = Session(title="Deck", entries=[], owner_id=uuid4())
        session.add_user_message("hi")
        session.add_assistant_message("hey")

        history = build_agent_history(session=session)

        user_messages = [m for m in history if isinstance(m, LLMUserMessage)]
        assert [m.content for m in user_messages] == ["hi"]

    def test_full_multi_turn_rendering_keeps_past_events_visible(self) -> None:
        """Golden output: a 5-turn history where the user pinned a track
        2 turns ago. The pinned event lives inside its bound UserMessage
        and remains visible on every later run — exactly what the LLM sees.

        The session transcript built below maps 1:1 to the asserted
        ``expected`` list, so you can read this test as a spec of how the
        agent perceives a multi-turn conversation with manual user actions.
        """
        session = Session(title="Deck", entries=[], owner_id=uuid4())

        # Turn 1 — user opens the deck, no manual changes yet.
        session.add_user_message("Bau mir ein 80er-Deck")
        session.add_assistant_message("Klar, ich starte mit ein paar Klassikern.")

        # Turn 2 — user pins a track BEFORE typing the next message.
        # The pin is recorded as a curation event and binds to turn-2's UserMessage.
        session.add_track(title="Take On Me", artist="a-ha", year=1985, is_pinned=True)
        session.add_user_message("der pin bleibt, sonst gerne austauschen")
        session.add_assistant_message("Verstanden, a-ha bleibt drin.")

        # Turn 3 — plain conversation, no manual change.
        # The earlier pin is now "2 turns ago" — it must still be visible.
        session.add_user_message("Mach es etwas tanzbarer")

        # Simulate that previous agent runs already consumed the pin event.
        # consumed=True must NOT hide it from history rendering.
        for event in session.user_curation_events:
            event.mark_consumed()

        history = build_agent_history(session=session)

        # The pin event's timestamp is generated at runtime — pull it out so
        # the golden output below stays deterministic.
        pin_event = session.user_curation_events[0]
        pin_iso = pin_event.occurred_at.isoformat()

        expected = [
            LLMUserMessage(content="Bau mir ein 80er-Deck"),
            LLMAssistantMessage(content="Klar, ich starte mit ein paar Klassikern."),
            LLMUserMessage(
                content=(
                    "<user_events>\n"
                    f'<event type="track_added" at="{pin_iso}">'
                    "a-ha - Take On Me</event>\n"
                    "</user_events>\n"
                    "\n"
                    "der pin bleibt, sonst gerne austauschen"
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
