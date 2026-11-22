from uuid import UUID

from fastapi_canon.integrations.websockets import CanonWebSocketRouter
from fastapi_canon.integrations.websockets.adapters.dishka import Dishka

from backend.features.session.presentation.rpc.channel import session_channel
from backend.features.session.presentation.rpc.context import SessionRpcContext
from backend.presentation.authentication import AuthenticatedUserId


async def session_rpc_context(
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
) -> SessionRpcContext:
    return SessionRpcContext(session_id=session_id, user_id=authenticated_user_id)


rpc_router = CanonWebSocketRouter(context=session_rpc_context, resolver=Dishka())
rpc_router.socket(
    "/api/v1/sessions/{session_id}/stream",
    channels=(session_channel,),
    name="session",
)
