import asyncio
from collections.abc import AsyncIterator
from typing import cast
from uuid import UUID, uuid4

from llm import OpenAIModelName

from backend.features.session.application import (
    SessionEvent,
    SessionConversationService,
    SessionService,
)
from backend.features.session.application.ports import (
    MessageAttachmentStore,
    StoredAttachment,
)
from backend.features.session.domain import (
    Session,
    UserCurationEvent,
    UserCurationEventType,
)
from backend.features.session.presentation.router import (
    complete_onboarding,
    get_session_by_id,
    restore_session_user_curation_event,
    submit_onboarding_answer,
    stop_message,
)
from backend.features.session.presentation.schemas import (
    SubmitOnboardingAnswerRequest,
    UserCurationEventTypeResponse,
)


class _SessionServiceStub:
    def __init__(self, session: Session) -> None:
        self._session = session
        self.received_session_id: UUID | None = None
        self.received_user_id: UUID | None = None
        self.received_restore_event_id: UUID | None = None

    async def get_by_id(self, *, session_id: UUID, user_id: UUID) -> Session:
        self.received_session_id = session_id
        self.received_user_id = user_id
        return self._session

    async def restore_user_curation_event(
        self, *, session_id: UUID, user_id: UUID, event_id: UUID
    ) -> Session:
        self.received_session_id = session_id
        self.received_user_id = user_id
        self.received_restore_event_id = event_id
        self._session.restore_user_curation_event(event_id=event_id)
        return self._session


class _SessionConversationServiceStub:
    def __init__(self) -> None:
        self.received_session_id: UUID | None = None
        self.received_user_id: UUID | None = None
        self.received_question_id: UUID | None = None
        self.received_answer: str | None = None
        self.received_answers: list[str] | None = None
        self.received_model_id: str | None = None

    async def stop_message(self, *, session_id: UUID, user_id: UUID) -> bool:
        self.received_session_id = session_id
        self.received_user_id = user_id
        return True

    async def submit_onboarding_answer(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        question_id: UUID,
        answer: str | None,
        answers: list[str] | None = None,
    ) -> Session:
        self.received_session_id = session_id
        self.received_user_id = user_id
        self.received_question_id = question_id
        self.received_answer = answer
        self.received_answers = answers
        return Session(title="Session", entries=[], owner_id=user_id, id=session_id)

    async def complete_onboarding(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        model_id: str | None = None,
    ) -> AsyncIterator[SessionEvent]:
        self.received_session_id = session_id
        self.received_user_id = user_id
        self.received_model_id = model_id
        if False:
            yield


class _MessageAttachmentStoreStub(MessageAttachmentStore):
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

    async def load_bytes(self, *, storage_key: str) -> bytes:
        return b""

    async def create_signed_url(
        self,
        *,
        storage_key: str,
        expires_in_seconds: int,
    ) -> str:
        return f"https://example.com/{storage_key}"

    async def delete_session_attachments(self, *, session_id) -> None:
        return None


async def _collect_stream_body(response) -> list[str]:
    return [chunk async for chunk in response.body_iterator]


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
                attachment_store=cast(
                    MessageAttachmentStore, _MessageAttachmentStoreStub()
                ),
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


class TestRestoreUserCurationEventRoute:
    def test_restores_event_and_returns_updated_session(self) -> None:
        session_id = uuid4()
        user_id = uuid4()
        session = Session(
            id=session_id,
            title="Session",
            entries=[],
            owner_id=user_id,
        )
        track = session.add_track(
            title="Starlight",
            artist="Muse",
            year=2006,
            is_pinned=False,
        )
        event = session.user_curation_events[0]
        service = _SessionServiceStub(session=session)

        response = asyncio.run(
            restore_session_user_curation_event(
                session_id=session_id,
                event_id=event.id,
                authenticated_user_id=user_id,
                service=cast(SessionService, service),
                attachment_store=cast(
                    MessageAttachmentStore, _MessageAttachmentStoreStub()
                ),
            )
        )

        assert service.received_session_id == session_id
        assert service.received_user_id == user_id
        assert service.received_restore_event_id == event.id
        assert response.unconsumed_user_curation_events == []
        assert response.playlist is not None
        assert all(t.id != track.id for t in response.playlist.tracks)


class TestStopMessageRoute:
    def test_stops_running_message_stream(self) -> None:
        session_id = uuid4()
        user_id = uuid4()
        service = _SessionConversationServiceStub()

        response = asyncio.run(
            stop_message(
                session_id=session_id,
                authenticated_user_id=user_id,
                service=cast(SessionConversationService, service),
            )
        )

        assert response.status_code == 204
        assert service.received_session_id == session_id
        assert service.received_user_id == user_id


class TestSubmitOnboardingAnswerRoute:
    def test_routes_answer_to_conversation_service(self) -> None:
        session_id = uuid4()
        user_id = uuid4()
        question_id = uuid4()
        service = _SessionConversationServiceStub()

        response = asyncio.run(
            submit_onboarding_answer(
                session_id=session_id,
                authenticated_user_id=user_id,
                body=SubmitOnboardingAnswerRequest(
                    question_id=question_id,
                    answer="Freunde",
                ),
                service=cast(SessionConversationService, service),
                attachment_store=cast(
                    MessageAttachmentStore, _MessageAttachmentStoreStub()
                ),
            )
        )

        assert service.received_session_id == session_id
        assert service.received_user_id == user_id
        assert service.received_question_id == question_id
        assert service.received_answer == "Freunde"
        assert service.received_answers == []
        assert response.id == session_id


class TestCompleteOnboardingRoute:
    def test_routes_last_answer_to_explicit_complete_operation(self) -> None:
        session_id = uuid4()
        user_id = uuid4()
        service = _SessionConversationServiceStub()

        response = asyncio.run(
            complete_onboarding(
                session_id=session_id,
                authenticated_user_id=user_id,
                service=cast(SessionConversationService, service),
            )
        )
        body = asyncio.run(_collect_stream_body(response))

        assert service.received_session_id == session_id
        assert service.received_user_id == user_id
        assert service.received_model_id is None
        assert response.media_type == "text/event-stream"
        assert body == ['event: done\ndata: {"type":"done"}\n\n']

    def test_passes_model_id_to_service(self) -> None:
        session_id = uuid4()
        user_id = uuid4()
        service = _SessionConversationServiceStub()

        response = asyncio.run(
            complete_onboarding(
                session_id=session_id,
                authenticated_user_id=user_id,
                service=cast(SessionConversationService, service),
                model_id=OpenAIModelName.GPT_5_4,
            )
        )
        body = asyncio.run(_collect_stream_body(response))

        assert service.received_model_id == OpenAIModelName.GPT_5_4
        assert body == ['event: done\ndata: {"type":"done"}\n\n']
