from uuid import UUID

from backend.features.auth.presentation.dependencies import AuthenticatedUserId
from backend.features.session.presentation.rpc.context import SessionRpcContext
from backend.features.session.presentation.rpc.contract import session_endpoint
from fastapi import APIRouter
from rpckit.dishka import Dishka
from rpckit.fastapi import RpcRoutes

rpc_router = APIRouter(prefix="/api/v1/sessions")


async def session_rpc_context(
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
) -> SessionRpcContext:
    return SessionRpcContext(session_id=session_id, user_id=authenticated_user_id)


RpcRoutes(rpc_router, context=session_rpc_context, resolver=Dishka()).mount(
    session_endpoint
)
