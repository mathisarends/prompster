from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from fastapi import FastAPI, WebSocketException, status
from fastapi.testclient import TestClient
from rpckit.dishka import Dishka
from starlette.websockets import WebSocketDisconnect

from backend.features.auth.presentation.dependencies import _get_authenticated_user_id
from backend.features.session.application import SessionConversationService
from backend.features.session.presentation.rpc.router import rpc_router


class ConversationStub:
    def __init__(self) -> None:
        self.received: tuple | None = None

    async def send_message(self, **kwargs) -> AsyncIterator:
        self.received = (kwargs["session_id"], kwargs["user_id"], kwargs["content"])
        if False:
            yield


class ResolverStub:
    def __init__(self, service: ConversationStub) -> None:
        self.service = service

    async def resolve(self, dependency: type):
        if dependency is SessionConversationService:
            return self.service
        raise LookupError(dependency)


def test_session_subscription_uses_authenticated_socket_context(monkeypatch) -> None:
    user_id = uuid4()
    session_id = uuid4()
    service = ConversationStub()
    app = FastAPI()
    app.include_router(rpc_router)
    app.dependency_overrides[_get_authenticated_user_id] = lambda: user_id
    app.state.dishka_container = object()
    monkeypatch.setattr(Dishka, "for_websocket", lambda *_: ResolverStub(service))

    with TestClient(app) as client:
        with client.websocket_connect(
            f"/api/v1/sessions/{session_id}/stream"
        ) as socket:
            socket.send_json(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "session.send_message.subscribe",
                    "params": {"content": "Hallo"},
                }
            )
            response = socket.receive_json()
            assert response["result"]["subscriptionId"] == "1"
            event = socket.receive_json()
            assert event["method"] == "session.send_message"
            assert event["params"]["payload"] == {"type": "done"}
            completed = socket.receive_json()
            assert completed["params"]["complete"] is True

    assert service.received == (session_id, user_id, "Hallo")


def test_session_socket_rejects_unauthenticated_connection() -> None:
    def reject_user() -> None:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

    app = FastAPI()
    app.include_router(rpc_router)
    app.dependency_overrides[_get_authenticated_user_id] = reject_user

    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect) as error:
            with client.websocket_connect(f"/api/v1/sessions/{uuid4()}/stream"):
                pass

    assert error.value.code == status.WS_1008_POLICY_VIOLATION
