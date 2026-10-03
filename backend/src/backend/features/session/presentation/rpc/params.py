from backend.features.session.presentation.schemas import SendMessageRequest
from rpckit import RpcModel


class SendMessageParams(SendMessageRequest, RpcModel):
    """Reuse attachment validation with the canonical RPC wire format."""

    model_id: str | None = None


class CompleteOnboardingParams(RpcModel):
    model_id: str | None = None
