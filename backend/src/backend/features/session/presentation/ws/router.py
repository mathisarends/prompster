from uuid import UUID

from dishka import AsyncContainer
from fastapi import APIRouter, WebSocket, status

from backend.features.auth.presentation.dependencies import AuthenticatedUserId
from backend.features.session.application import GetSessionByIdHandler
from backend.features.session.domain import (
    Session,
    SessionAccessDeniedError,
    SessionNotFoundError,
)
from backend.features.session.presentation.ws.connection import (
    SessionWebSocketConnection,
)
from backend.features.session.presentation.ws.events import WebSocketEventCatalog

ws_router = APIRouter(prefix="/sessions", tags=["sessions-ws"])


@ws_router.get(
    "/ws/schemas",
    response_model=WebSocketEventCatalog,
    status_code=status.HTTP_200_OK,
    operation_id="get_session_ws_schemas",
)
async def get_session_ws_schemas() -> WebSocketEventCatalog:
    return WebSocketEventCatalog()


@ws_router.websocket("/ws/{session_id}")
async def session_websocket(
    websocket: WebSocket,
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
) -> None:
    container: AsyncContainer = websocket.app.state.dishka_container

    try:
        session = await _load_session(
            container,
            session_id=session_id,
            user_id=authenticated_user_id,
        )
    except SessionNotFoundError:
        await _close_policy_violation(websocket, reason="Session not found")
        return
    except SessionAccessDeniedError:
        await _close_policy_violation(websocket, reason="Session access denied")
        return

    connection = SessionWebSocketConnection(
        websocket=websocket,
        container=container,
        session_id=session_id,
        session=session,
    )
    await connection.run()


async def _load_session(
    container: AsyncContainer,
    *,
    session_id: UUID,
    user_id: UUID,
) -> Session:
    async with container() as request_container:
        handler = await request_container.get(GetSessionByIdHandler)
        return await handler.handle(session_id=session_id, user_id=user_id)


async def _close_policy_violation(websocket: WebSocket, *, reason: str) -> None:
    await websocket.close(
        code=status.WS_1008_POLICY_VIOLATION,
        reason=reason,
    )
