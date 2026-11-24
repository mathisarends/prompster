import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast, get_args
from unittest.mock import Mock
from uuid import UUID

import pytest
from dishka import AsyncContainer, Provider, Scope, provide
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient
from fastapi_canon import APIRouter, Composition, Feature, ServiceScope

from backend.features.session.application import (
    SessionAssistantMessageChunk,
    SessionConversationService,
    SessionSpotifyPlaylistExporter,
)
from backend.features.session.application.ports import MessageAttachmentStore
from backend.features.session.application.ports.session_runner import (
    SessionRunner,
    SessionRunnerAssistantMessageChunk,
)
from backend.features.session.application.ports.title_generator import (
    SessionTitleGenerator,
)
from backend.features.session.domain import (
    Session,
    SessionRepository,
)
from backend.features.session.presentation.schemas import (
    CompleteOnboardingRequest,
    SendMessageRequest,
)
from backend.features.session.presentation.streams.events import (
    PlaylistPayload,
    SessionSnapshotPayload,
    SessionStreamEvent,
)
from backend.features.session.presentation.streams.router import (
    complete_onboarding,
    send_message,
    stream_router,
)
from backend.presentation.authentication import (
    AuthCookieSettings,
    get_authenticated_user_id,
)
from backend.shared.authentication import TokenIssuer

_USER_ID = UUID(int=3)
_SESSION_ID = UUID(int=2)


class _ConversationStub:
    def __init__(self) -> None:
        self.received: tuple | None = None
        self.model_id: str | None = None

    async def send_message(self, **kwargs) -> AsyncIterator:
        self.received = (kwargs["session_id"], kwargs["user_id"], kwargs["content"])
        self.model_id = kwargs["model_id"]
        yield SessionAssistantMessageChunk(message_id=UUID(int=5), chunk="Hallo")


def _scope(service: object) -> ServiceScope[SessionConversationService]:
    @asynccontextmanager
    async def open_scope() -> AsyncIterator[object]:
        yield service

    return cast(ServiceScope[SessionConversationService], open_scope)


class _StreamDependencies(Provider):
    """APP bindings the stream routes need besides the conversation service."""

    @provide(scope=Scope.APP)
    def cookies(self) -> AuthCookieSettings:
        return Mock(spec=AuthCookieSettings)

    @provide(scope=Scope.APP)
    def tokens(self) -> TokenIssuer:
        return Mock(spec=TokenIssuer)

    @provide(scope=Scope.APP)
    def exporters(self) -> ServiceScope[SessionSpotifyPlaylistExporter]:
        return Mock(spec=ServiceScope)


def _session_app(provider: Provider, user_id_factory) -> FastAPI:
    app = FastAPI()
    feature = Feature(
        name="session",
        routers=[stream_router],
        providers=[provider, _StreamDependencies()],
    )
    Composition(
        features=[feature], router_factory=lambda: APIRouter(prefix="/api/v1")
    ).build(app)
    app.dependency_overrides[get_authenticated_user_id] = user_id_factory
    return app


def _conversation_provider(service: object) -> Provider:
    class ConversationProvider(Provider):
        @provide(scope=Scope.REQUEST)
        def conversation(self) -> SessionConversationService:
            return cast(SessionConversationService, service)

        @provide(scope=Scope.APP)
        def conversations(
            self, container: AsyncContainer
        ) -> ServiceScope[SessionConversationService]:
            return ServiceScope(container, SessionConversationService)

    return ConversationProvider()


def _sse_frames(body: str) -> list[tuple[str, dict]]:
    frames = []
    for block in body.replace("\r\n", "\n").strip().split("\n\n"):
        fields = {}
        for line in block.splitlines():
            name, _, value = line.partition(":")
            fields[name] = value.strip()
        if "data" in fields:
            event = fields.get("event", "message")
            frames.append((event, json.loads(fields["data"])))
    return frames


def test_event_union_has_discriminated_model_members() -> None:
    event_classes = get_args(get_args(SessionStreamEvent.__value__)[0])
    assert all("type" in cls.model_fields for cls in event_classes)
    assert "type" not in PlaylistPayload.model_fields
    assert "type" not in SessionSnapshotPayload.model_fields


def test_send_message_streams_server_sent_events_for_the_authenticated_user() -> None:
    service = _ConversationStub()
    app = _session_app(_conversation_provider(service), lambda: _USER_ID)

    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/sessions/{_SESSION_ID}/messages",
            json={"content": "Hallo", "modelId": "test-model"},
        )

    assert response.headers["content-type"].startswith("text/event-stream")
    assert _sse_frames(response.text) == [
        (
            "message",
            {
                "type": "message.assistant_chunk",
                "messageId": str(UUID(int=5)),
                "chunk": "Hallo",
            },
        ),
        ("message", {"type": "done"}),
        ("canon.complete", {}),
    ]
    assert service.received == (_SESSION_ID, _USER_ID, "Hallo")
    assert service.model_id == "test-model"


@pytest.mark.parametrize(
    "body",
    [{"content": ""}, {"content": "x" * 4001}],
)
def test_invalid_bodies_are_rejected_before_the_stream_starts(body) -> None:
    app = _session_app(_conversation_provider(_ConversationStub()), lambda: _USER_ID)

    with TestClient(app) as client:
        response = client.post(f"/api/v1/sessions/{_SESSION_ID}/messages", json=body)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_unauthenticated_requests_never_open_a_stream() -> None:
    def reject_user() -> None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    app = _session_app(_conversation_provider(_ConversationStub()), reject_user)

    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/sessions/{_SESSION_ID}/messages", json={"content": "Hallo"}
        )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert not response.headers["content-type"].startswith("text/event-stream")


@pytest.mark.parametrize("operation", ["send_message", "complete_onboarding"])
def test_closing_the_stream_closes_the_application_stream_immediately(
    operation,
) -> None:
    closed = False

    async def source():
        nonlocal closed
        try:
            yield SessionAssistantMessageChunk(message_id=UUID(int=1), chunk="Hallo")
            await asyncio.Event().wait()
        finally:
            closed = True

    service = Mock(spec=SessionConversationService)
    getattr(service, operation).return_value = source()

    async def run():
        stream = (
            send_message(
                _SESSION_ID,
                SendMessageRequest(content="Hallo"),
                _USER_ID,
                _scope(service),
            )
            if operation == "send_message"
            else complete_onboarding(
                _SESSION_ID, CompleteOnboardingRequest(), _USER_ID, _scope(service)
            )
        )
        event = await anext(stream)
        await stream.aclose()
        return event

    event = asyncio.run(run())

    assert event.chunk == "Hallo"
    assert closed


def test_closing_the_stream_closes_runner_and_awaits_title_task():
    owner_id = UUID(int=4)
    session = Session.create(title="", owner_id=owner_id)
    repository = Mock(spec=SessionRepository)
    repository.get_by_id.return_value = session
    repository.save.return_value = session
    runner = Mock(spec=SessionRunner)
    title_generator = Mock(spec=SessionTitleGenerator)
    runner_closed = False
    title_closed = False

    async def runner_events(**kwargs):
        nonlocal runner_closed
        try:
            await asyncio.sleep(0)
            yield SessionRunnerAssistantMessageChunk(chunk="Hallo")
            await asyncio.Event().wait()
        finally:
            runner_closed = True

    async def generate_title(**kwargs):
        nonlocal title_closed
        try:
            await asyncio.Event().wait()
        finally:
            title_closed = True

    runner.run.side_effect = runner_events
    title_generator.generate.side_effect = generate_title
    service = SessionConversationService(
        session_repository=repository,
        runner=runner,
        message_attachment_store=Mock(spec=MessageAttachmentStore),
        title_generator=title_generator,
    )

    async def run():
        stream = send_message(
            session.id, SendMessageRequest(content="Hallo"), owner_id, _scope(service)
        )
        event = await anext(stream)
        await stream.aclose()
        return event

    event = asyncio.run(run())

    assert event.type == "message.assistant_started"
    assert runner_closed
    assert title_closed


def test_stream_owns_its_service_scope_until_the_stream_closes() -> None:
    lifecycle: list[str] = []

    class StreamingConversation:
        async def send_message(self, **kwargs):
            try:
                yield SessionAssistantMessageChunk(
                    message_id=UUID(int=5), chunk="Hallo"
                )
            finally:
                lifecycle.append("stream_closed")

    class ConversationProvider(Provider):
        @provide(scope=Scope.REQUEST)
        async def conversation(self) -> AsyncIterator[SessionConversationService]:
            lifecycle.append("scope_opened")
            try:
                yield cast(SessionConversationService, StreamingConversation())
            finally:
                lifecycle.append("scope_closed")

        @provide(scope=Scope.APP)
        def conversations(
            self, container: AsyncContainer
        ) -> ServiceScope[SessionConversationService]:
            return ServiceScope(container, SessionConversationService)

    app = _session_app(ConversationProvider(), lambda: _USER_ID)

    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/sessions/{_SESSION_ID}/messages", json={"content": "Hallo"}
        )

    assert [event for event, _ in _sse_frames(response.text)][-1] == "canon.complete"
    assert lifecycle == ["scope_opened", "stream_closed", "scope_closed"]
