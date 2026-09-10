from backend.features.auth.presentation.exception_handlers import AUTH_ERRORS
from backend.features.payment.application import (
    PaymentGatewayError,
    PaymentWebhookVerificationError,
)
from fastapi import status
from fastapi_canon import Error, ErrorRegistry

PAYMENT_GATEWAY_ERROR = Error(
    PaymentGatewayError,
    status=status.HTTP_400_BAD_REQUEST,
    code="payment_gateway_error",
    title="Payment request failed",
)
PAYMENT_WEBHOOK_VERIFICATION_ERROR = Error(
    PaymentWebhookVerificationError,
    status=status.HTTP_400_BAD_REQUEST,
    code="payment_webhook_verification_error",
    title="Payment webhook verification failed",
)

PAYMENT_ERRORS = ErrorRegistry.merge(
    AUTH_ERRORS,
    ErrorRegistry(
        name="payment_domain",
        errors=(PAYMENT_GATEWAY_ERROR, PAYMENT_WEBHOOK_VERIFICATION_ERROR),
    ),
    name="payment",
)
