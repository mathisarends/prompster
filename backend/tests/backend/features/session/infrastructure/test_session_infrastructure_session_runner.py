import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from uuid import uuid4

from llmify.messages import UserMessage
from agent import UserEvent

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
    _to_user_events,
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


class TestSessionRunnerMessageContext:
    def test_adds_unconsumed_user_curation_events_to_message_context(self) -> None:
        event = UserCurationEvent(
            id=uuid4(),
            event_type=UserCurationEventType.TRACK_REMOVED,
            track_id=uuid4(),
            track_title="Umbrella",
            track_artist="Rihanna",
            track_spotify_uri="spotify:track:1",
            track_cover_url="https://example.com/cover.jpg",
            created_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        consumed_event = UserCurationEvent(
            event_type=UserCurationEventType.TRACK_PINNED,
            track_id=uuid4(),
            track_title="Consumed",
            track_artist="Artist",
            consumed=True,
        )
        session = Session(
            title="Deck",
            entries=[],
            owner_id=uuid4(),
            user_curation_events=[event, consumed_event],
        )

        history = _to_history_messages(session=session)
        user_events = _to_user_events(session=session)

        user_messages = [
            message for message in history if isinstance(message, UserMessage)
        ]
        assert user_messages == []
        assert user_events == [
            UserEvent(
                type="track_removed",
                track_title="Umbrella",
                track_artist="Rihanna",
                occurred_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                history_index=0,
            )
        ]

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
