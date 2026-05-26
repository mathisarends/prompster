import asyncio
from typing import cast
from uuid import UUID, uuid4

from backend.features.session.application import SessionService
from backend.features.session.domain import (
    Session,
    UserCurationEvent,
    UserCurationEventType,
)
from backend.features.session.presentation.router import get_session_by_id
from backend.features.session.presentation.schemas import UserCurationEventTypeResponse


class _SessionServiceStub:
    def __init__(self, session: Session) -> None:
        self._session = session
        self.received_session_id: UUID | None = None
        self.received_user_id: UUID | None = None

    async def get_by_id(self, *, session_id: UUID, user_id: UUID) -> Session:
        self.received_session_id = session_id
        self.received_user_id = user_id
        return self._session


class TestGetSessionByIdRoute:
    def test_returns_unconsumed_user_curation_events_only(self) -> None:
        session_id = uuid4()
        user_id = uuid4()
        consumed_track_id = uuid4()
        unconsumed_track_id = uuid4()

        consumed_event = UserCurationEvent(
            event_type=UserCurationEventType.TRACK_ADDED,
            track_id=consumed_track_id,
            track_title="Consumed",
            track_artist="Artist A",
            consumed=True,
        )
        unconsumed_event = UserCurationEvent(
            event_type=UserCurationEventType.TRACK_PINNED,
            track_id=unconsumed_track_id,
            track_title="Unconsumed",
            track_artist="Artist B",
            consumed=False,
        )

        session = Session(
            id=session_id,
            title="Session",
            entries=[],
            owner_id=user_id,
            user_curation_events=[consumed_event, unconsumed_event],
        )
        service = _SessionServiceStub(session=session)

        response = asyncio.run(
            get_session_by_id(
                session_id=session_id,
                authenticated_user_id=user_id,
                service=cast(SessionService, service),
            )
        )

        assert service.received_session_id == session_id
        assert service.received_user_id == user_id
        assert len(response.unconsumed_user_curation_events) == 1
        assert response.unconsumed_user_curation_events[0].id == unconsumed_event.id
        assert (
            response.unconsumed_user_curation_events[0].event_type
            == UserCurationEventTypeResponse.TRACK_PINNED
        )
