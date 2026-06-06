from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from backend.features.payment.application import (
    PaymentGatewayError,
    PaymentWebhookVerificationError,
)


def _exception_detail(exc: Exception, *, fallback: str) -> str:
    detail = str(exc).strip()
    return detail if detail else fallback


async def _payment_gateway_error_handler(
    _: Request,
    exc: PaymentGatewayError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": _exception_detail(exc, fallback="Payment request failed")},
    )


async def _payment_webhook_verification_error_handler(
    _: Request,
    exc: PaymentWebhookVerificationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": _exception_detail(
                exc,
                fallback="Payment webhook verification failed",
            )
        },
    )


def register_payment_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(
        PaymentWebhookVerificationError,
        _payment_webhook_verification_error_handler,
    )
    app.add_exception_handler(PaymentGatewayError, _payment_gateway_error_handler)
