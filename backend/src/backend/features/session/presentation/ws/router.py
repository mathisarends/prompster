from uuid import UUID

from dishka import AsyncContainer
from fastapi import APIRouter, WebSocket, status

from backend.features.auth.presentation.dependencies import AuthenticatedUserId
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
    connection = SessionWebSocketConnection(
        websocket=websocket,
        container=container,
        session_id=session_id,
        user_id=authenticated_user_id,
    )
    await connection.run()
