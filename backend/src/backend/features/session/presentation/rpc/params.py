from fastapi_canon.integrations.websockets import RpcModel

from backend.features.session.presentation.schemas import SendMessageRequest


class SendMessageParams(SendMessageRequest, RpcModel):
    """Reuse attachment validation with the canonical RPC wire format."""

    model_id: str | None = None


class CompleteOnboardingParams(RpcModel):
    model_id: str | None = None
