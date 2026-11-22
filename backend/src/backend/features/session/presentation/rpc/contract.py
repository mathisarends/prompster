from backend.features.session.presentation.rpc.router import rpc_router

contract = rpc_router.contract(
    title="Prompster session streams",
    base_url="ws://localhost:8000",
)
