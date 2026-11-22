import asyncio
from collections.abc import AsyncIterator
from threading import Event
from uuid import UUID

import pytest
from dishka import Provider, Scope, provide
from fastapi import FastAPI, WebSocketException, status
from fastapi.testclient import TestClient
from fastapi_canon import Composition, Feature
from starlette.websockets import WebSocketDisconnect

from backend.features.session.application import (
    SessionAssistantMessageChunk,
    SessionConversationService,
)
from backend.features.session.presentation.rpc import rpc_router
from backend.presentation.authentication import get_authenticated_user_id


class ConversationStub:
    def __init__(self) -> None:
        self.received: tuple | None = None
        self.model_id: str | None = None

    async def send_message(self, **kwargs) -> AsyncIterator:
        self.received = (kwargs["session_id"], kwargs["user_id"], kwargs["content"])
        self.model_id = kwargs["model_id"]
        if False:
            yield


def _conversation_provider(service: object) -> Provider:
    provider = Provider(scope=Scope.REQUEST)
    provider.provide(lambda: service, provides=SessionConversationService)
    return provider


def _session_app(provider: Provider, user_id_factory) -> FastAPI:
    app = FastAPI()
    app.include_router(rpc_router)
    Composition(features=[Feature(name="session", providers=[provider])]).build(app)
    app.dependency_overrides[get_authenticated_user_id] = user_id_factory
    return app


def test_session_stream_uses_authenticated_socket_context() -> None:
    user_id = UUID(int=1)
    session_id = UUID(int=2)
    service = ConversationStub()
    app = _session_app(_conversation_provider(service), lambda: user_id)

    with (
        TestClient(app) as client,
        client.websocket_connect(f"/api/v1/sessions/{session_id}/stream") as socket,
    ):
        socket.send_json(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "session.send_message.open",
                "params": {"content": "Hallo", "modelId": "test-model"},
            }
        )
        response = socket.receive_json()
        assert response["result"]["streamId"]
        event = socket.receive_json()
        assert event["method"] == "session.send_message"
        assert event["params"]["payload"] == {"type": "done"}
        completed = socket.receive_json()
        assert completed["params"]["complete"] is True

    assert service.received == (session_id, user_id, "Hallo")
    assert service.model_id == "test-model"


@pytest.mark.parametrize(
    "params",
    [{"content": ""}, {"content": "Hallo", "userId": str(UUID(int=3))}],
)
def test_session_stream_rejects_invalid_params(params) -> None:
    app = _session_app(_conversation_provider(ConversationStub()), lambda: UUID(int=8))

    with (
        TestClient(app) as client,
        client.websocket_connect(f"/api/v1/sessions/{UUID(int=4)}/stream") as socket,
    ):
        socket.send_json(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "session.send_message.open",
                "params": params,
            }
        )
        response = socket.receive_json()
        assert response["error"]["code"] == -32602


@pytest.mark.parametrize("termination", ["cancel", "disconnect"])
def test_session_stream_closes_stream_before_dishka_request_scope(termination):
    lifecycle: list[str] = []
    scope_closed = Event()

    class StreamingConversation:
        async def send_message(self, **kwargs):
            try:
                yield SessionAssistantMessageChunk(
                    message_id=UUID(int=5), chunk="Hallo"
                )
                await asyncio.Event().wait()
            finally:
                lifecycle.append("stream_closed")

    class ConversationProvider(Provider):
        @provide(scope=Scope.REQUEST)
        async def conversation(self) -> AsyncIterator[SessionConversationService]:
            lifecycle.append("request_opened")
            try:
                yield StreamingConversation()
            finally:
                lifecycle.append("request_closed")
                scope_closed.set()

    app = _session_app(ConversationProvider(), lambda: UUID(int=9))

    with TestClient(app) as client:
        with client.websocket_connect(
            f"/api/v1/sessions/{UUID(int=6)}/stream"
        ) as socket:
            socket.send_json(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "session.send_message.open",
                    "params": {"content": "Hallo"},
                }
            )
            stream_id = socket.receive_json()["result"]["streamId"]
            event = socket.receive_json()
            assert event["params"]["payload"]["chunk"] == "Hallo"
            assert lifecycle == ["request_opened"]
            if termination == "cancel":
                socket.send_json(
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "session.send_message.cancel",
                        "params": {"streamId": stream_id},
                    }
                )
                assert socket.receive_json() == {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "result": None,
                }
                socket.send_json({"jsonrpc": "2.0", "id": 3, "method": "session.ping"})
                assert socket.receive_json()["result"] == "pong"
        assert scope_closed.wait(timeout=2)

    assert lifecycle == ["request_opened", "stream_closed", "request_closed"]


def test_session_socket_rejects_unauthenticated_connection() -> None:
    def reject_user() -> None:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

    app = _session_app(_conversation_provider(ConversationStub()), reject_user)

    with (
        TestClient(app) as client,
        pytest.raises(WebSocketDisconnect) as error,
        client.websocket_connect(f"/api/v1/sessions/{UUID(int=7)}/stream"),
    ):
        pass

    assert error.value.code == status.WS_1008_POLICY_VIOLATION
