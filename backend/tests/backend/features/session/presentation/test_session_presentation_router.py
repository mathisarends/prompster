import asyncio
from collections.abc import AsyncIterator
from io import BytesIO
from typing import cast
from uuid import UUID, uuid4

from backend.features.session.application import (
    ImageAttachmentService,
    SessionConversationService,
    SessionEvent,
    SessionImageAttachmentReference,
    SessionImageAttachmentUpload,
    SessionImageUrlResolver,
    SessionMessageAttachment,
    SessionService,
    StashedImageAttachment,
)
from backend.features.session.application.ports import (
    MessageAttachmentStore,
    StoredAttachment,
)
from backend.features.session.domain import (
    ImageAttachment,
    Session,
    UserCurationEvent,
    UserCurationEventType,
)
from backend.features.session.presentation.image_attachment_router import (
    upload_image_attachment,
)
from backend.features.session.presentation.router import (
    create_session,
    get_session_by_id,
    restore_session_user_curation_event,
    stop_message,
    submit_onboarding_answer,
)
from backend.features.session.presentation.rpc.router import (
    CompleteOnboardingParams,
    SendMessageParams,
    SessionRpcContext,
    complete_onboarding,
    send_message,
)
from backend.features.session.presentation.schemas import (
    SessionMessageAttachmentKind,
    SessionMessageAttachmentRequest,
    SubmitOnboardingAnswerRequest,
    UserCurationEventTypeResponse,
)
from fastapi import UploadFile
from starlette.datastructures import Headers


class _SessionServiceStub:
    def __init__(self, session: Session) -> None:
        self._session = session
        self.received_session_id: UUID | None = None
        self.received_user_id: UUID | None = None
        self.received_owner_id: UUID | None = None
        self.received_restore_event_id: UUID | None = None

    async def get_by_id(self, *, session_id: UUID, user_id: UUID) -> Session:
        self.received_session_id = session_id
        self.received_user_id = user_id
        return self._session

    async def create(self, *, owner_id: UUID) -> Session:
        self.received_owner_id = owner_id
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
        self.received_content: str | None = None
        self.received_attachments: list[SessionMessageAttachment] | None = None
        self.received_image_attachments: (
            list[SessionImageAttachmentReference] | None
        ) = None
        self.received_upload: SessionImageAttachmentUpload | None = None
        self.received_question_id: UUID | None = None
        self.received_answer: str | None = None
        self.received_answers: list[str] | None = None
        self.received_model_id: str | None = None

    async def send_message(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        content: str,
        attachments: list[SessionMessageAttachment] | None = None,
        image_attachments: list[SessionImageAttachmentReference] | None = None,
        model_id: str | None = None,
    ) -> AsyncIterator[SessionEvent]:
        self.received_session_id = session_id
        self.received_user_id = user_id
        self.received_content = content
        self.received_attachments = attachments
        self.received_image_attachments = image_attachments
        self.received_model_id = model_id
        if False:
            yield

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
    def __init__(self) -> None:
        self.signed_url_requests: list[tuple[str, int]] = []

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
        self.signed_url_requests.append((storage_key, expires_in_seconds))
        return f"https://example.com/{storage_key}"

    async def delete_session_attachments(self, *, user_id, session_id) -> None:
        return None

    async def delete_user_attachments(self, *, user_id) -> None:
        return None


class _ImageAttachmentServiceStub:
    def __init__(self) -> None:
        self.received_user_id: UUID | None = None
        self.received_upload: SessionImageAttachmentUpload | None = None

    async def stash_image(
        self,
        *,
        user_id: UUID,
        image: SessionImageAttachmentUpload,
    ) -> StashedImageAttachment:
        self.received_user_id = user_id
        self.received_upload = image
        return StashedImageAttachment(
            id=uuid4(),
            storage_key=f"users/{user_id}/stash/uploaded.png",
            content_type=image.content_type,
            file_name=image.file_name,
            size_bytes=len(image.content),
        )


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
            event_type=UserCurationEventType.TRACK_REMOVED,
            track_id=unconsumed_track_id,
            track_title="Unconsumed",
            track_artist="Artist B",
            track_year=2006,
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
                image_url_resolver=SessionImageUrlResolver(
                    _MessageAttachmentStoreStub()
                ),
            )
        )

        assert service.received_session_id == session_id
        assert service.received_user_id == user_id
        assert len(response.unconsumed_user_curation_events) == 1
        assert response.unconsumed_user_curation_events[0].id == unconsumed_event.id
        assert (
            response.unconsumed_user_curation_events[0].event_type
            == UserCurationEventTypeResponse.TRACK_REMOVED
        )

    def test_returns_signed_image_attachment_urls(self) -> None:
        session_id = uuid4()
        user_id = uuid4()
        storage_key = f"users/{user_id}/chat/{session_id}/image.png"
        session = Session(
            id=session_id,
            title="Session",
            entries=[],
            owner_id=user_id,
        )
        session.add_user_message(
            content="See image",
            image_attachments=[
                ImageAttachment(
                    storage_key=storage_key,
                    content_type="image/png",
                    file_name="image.png",
                    size_bytes=123,
                )
            ],
        )
        service = _SessionServiceStub(session=session)
        attachment_store = _MessageAttachmentStoreStub()

        response = asyncio.run(
            get_session_by_id(
                session_id=session_id,
                authenticated_user_id=user_id,
                service=cast(SessionService, service),
                image_url_resolver=SessionImageUrlResolver(attachment_store),
            )
        )

        first_entry = response.entries[0]
        assert first_entry.kind == "user_message"
        assert first_entry.image_attachments == [f"https://example.com/{storage_key}"]
        assert attachment_store.signed_url_requests == [(storage_key, 86_400)]


class TestCreateSessionRoute:
    def test_creates_empty_session(self) -> None:
        user_id = uuid4()
        session = Session(
            title="",
            entries=[],
            owner_id=user_id,
        )
        service = _SessionServiceStub(session=session)

        response = asyncio.run(
            create_session(
                authenticated_user_id=user_id,
                service=cast(SessionService, service),
                image_url_resolver=SessionImageUrlResolver(
                    _MessageAttachmentStoreStub()
                ),
            )
        )

        assert service.received_owner_id == user_id
        assert response.id == session.id
        assert response.title == ""


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
        )
        event = session.user_curation_events[0]
        service = _SessionServiceStub(session=session)

        response = asyncio.run(
            restore_session_user_curation_event(
                session_id=session_id,
                event_id=event.id,
                authenticated_user_id=user_id,
                service=cast(SessionService, service),
                image_url_resolver=SessionImageUrlResolver(
                    _MessageAttachmentStoreStub()
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


class TestSendMessageSubscription:
    def test_routes_json_body_to_conversation_service(self) -> None:
        session_id = uuid4()
        user_id = uuid4()
        service = _SessionConversationServiceStub()

        async def collect():
            return [
                event
                async for event in send_message(
                    params=SendMessageParams(
                        content="Hallo",
                        attachments=[
                            SessionMessageAttachmentRequest(
                                kind=SessionMessageAttachmentKind.SPOTIFY_ARTIST,
                                external_id="artist-1",
                                title="Artist 1",
                            )
                        ],
                        model_id="gpt-6-terra-US",
                    ),
                    context=SessionRpcContext(session_id=session_id, user_id=user_id),
                    service=cast(SessionConversationService, service),
                )
            ]

        events = asyncio.run(collect())

        assert service.received_session_id == session_id
        assert service.received_user_id == user_id
        assert service.received_content == "Hallo"
        assert service.received_attachments is not None
        assert len(service.received_attachments) == 1
        assert service.received_attachments[0].external_id == "artist-1"
        assert service.received_image_attachments == []
        assert service.received_model_id == "gpt-6-terra-US"
        assert [event.type for event in events] == ["done"]


class TestUploadImageAttachmentRoute:
    def test_uploads_image_and_returns_reference(self) -> None:
        user_id = uuid4()
        service = _ImageAttachmentServiceStub()
        file = UploadFile(
            file=BytesIO(b"1234"),
            filename="shot.png",
            headers=Headers({"content-type": "image/png"}),
        )

        response = asyncio.run(
            upload_image_attachment(
                authenticated_user_id=user_id,
                service=cast(ImageAttachmentService, service),
                attachment_store=cast(
                    MessageAttachmentStore, _MessageAttachmentStoreStub()
                ),
                file=file,
            )
        )

        assert service.received_user_id == user_id
        assert service.received_upload is not None
        assert service.received_upload.content == b"1234"
        assert response.storage_key == f"users/{user_id}/stash/uploaded.png"
        assert response.url == f"https://example.com/{response.storage_key}"
        assert response.content_type == "image/png"
        assert response.file_name == "shot.png"
        assert response.size_bytes == 4


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
                image_url_resolver=SessionImageUrlResolver(
                    _MessageAttachmentStoreStub()
                ),
            )
        )

        assert service.received_session_id == session_id
        assert service.received_user_id == user_id
        assert service.received_question_id == question_id
        assert service.received_answer == "Freunde"
        assert service.received_answers == []
        assert response.id == session_id


class TestCompleteOnboardingSubscription:
    def test_routes_last_answer_to_explicit_complete_operation(self) -> None:
        session_id = uuid4()
        user_id = uuid4()
        service = _SessionConversationServiceStub()

        async def collect():
            return [
                event
                async for event in complete_onboarding(
                    params=CompleteOnboardingParams(),
                    context=SessionRpcContext(session_id=session_id, user_id=user_id),
                    service=cast(SessionConversationService, service),
                )
            ]

        events = asyncio.run(collect())

        assert service.received_session_id == session_id
        assert service.received_user_id == user_id
        assert service.received_model_id is None
        assert [event.type for event in events] == ["done"]

    def test_passes_model_id_to_service(self) -> None:
        session_id = uuid4()
        user_id = uuid4()
        service = _SessionConversationServiceStub()

        async def collect():
            return [
                event
                async for event in complete_onboarding(
                    params=CompleteOnboardingParams(model_id="gpt-6-terra-US"),
                    context=SessionRpcContext(session_id=session_id, user_id=user_id),
                    service=cast(SessionConversationService, service),
                )
            ]

        events = asyncio.run(collect())

        assert service.received_model_id == "gpt-6-terra-US"
        assert [event.type for event in events] == ["done"]
