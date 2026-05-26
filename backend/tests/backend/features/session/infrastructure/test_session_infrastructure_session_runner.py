import asyncio
import json
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from uuid import uuid4

from llmify.messages import UserMessage

from backend.features.session.application import SessionConversationService
from backend.features.session.application.ports.session_runner import (
    SessionRunner,
    SessionRunnerEvent,
)
from backend.features.session.domain import (
    Session,
    SessionRepository,
    WorkspaceEvent,
    WorkspaceEventType,
)
from backend.features.session.infrastructure.session_runner import _to_message_manager


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
    def test_adds_unconsumed_workspace_events_to_message_context(self) -> None:
        event = WorkspaceEvent(
            id=uuid4(),
            event_type=WorkspaceEventType.TRACK_REMOVED,
            track_id=uuid4(),
            track_title="Umbrella",
            track_artist="Rihanna",
            track_spotify_uri="spotify:track:1",
            track_cover_url="https://example.com/cover.jpg",
            created_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        consumed_event = WorkspaceEvent(
            event_type=WorkspaceEventType.TRACK_PINNED,
            track_id=uuid4(),
            track_title="Consumed",
            track_artist="Artist",
            consumed=True,
        )
        session = Session(
            title="Deck",
            entries=[],
            owner_id=uuid4(),
            workspace_events=[event, consumed_event],
        )

        manager = _to_message_manager(session=session, system_prompt="System")

        user_messages = [
            message for message in manager.all() if isinstance(message, UserMessage)
        ]
        payload = json.loads(user_messages[-1].content)
        context = payload["manual_playlist_changes_since_last_response"]
        assert context["track_removed_means_do_not_readd_unless_requested"] is True
        assert context["track_pinned_means_hard_constraint"] is True
        assert context["events"] == [
            {
                "type": "track_removed",
                "track_id": str(event.track_id),
                "track_title": "Umbrella",
                "track_artist": "Rihanna",
                "track_spotify_uri": "spotify:track:1",
                "track_cover_url": "https://example.com/cover.jpg",
                "occurred_at": "2026-01-01T00:00:00+00:00",
            }
        ]

    def test_send_message_consumes_workspace_events_after_runner(self) -> None:
        user_id = uuid4()
        event = WorkspaceEvent(
            event_type=WorkspaceEventType.TRACK_PINNED,
            track_id=uuid4(),
            track_title="Umbrella",
            track_artist="Rihanna",
        )
        session = Session(
            title="Deck",
            entries=[],
            owner_id=user_id,
            workspace_events=[event],
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
