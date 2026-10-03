from backend.features.session.presentation.rpc.channel import session_channel
from backend.features.session.presentation.rpc.context import SessionRpcContext
from rpckit import RpcService

rpc_service = RpcService()
session_endpoint = rpc_service.socket(
    "/api/v1/sessions/{session_id}/stream",
    channels=(session_channel,),
    name="session",
    context=SessionRpcContext,
)
contract = rpc_service.contract(
    title="Prompster session streams",
    base_url="ws://localhost:8000",
)
