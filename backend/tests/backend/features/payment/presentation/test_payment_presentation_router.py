import asyncio
from decimal import Decimal
from typing import cast
from uuid import uuid4

import pytest
from backend.features.payment.application import (
    CheckoutSession,
    PaymentGateway,
    PaymentIntent,
    PaymentWebhookVerificationError,
)
from backend.features.payment.presentation.router import (
    create_checkout_session,
    create_coupon,
    verify_webhook,
)
from backend.features.payment.presentation.schemas import (
    CreateCheckoutSessionRequest,
    CreateCouponRequest,
)
from starlette.requests import Request


class _PaymentGatewayStub:
    def __init__(self) -> None:
        self.received_amount: Decimal | None = None
        self.received_currency: str | None = None
        self.received_success_url: str | None = None
        self.received_cancel_url: str | None = None
        self.received_metadata: dict[str, str] | None = None
        self.received_coupon_code: str | None = None
        self.received_coupon: tuple[str, int, int] | None = None
        self.received_payload: bytes | None = None
        self.received_signature: str | None = None

    async def create_checkout_session(
        self,
        amount: Decimal,
        currency: str,
        success_url: str,
        cancel_url: str,
        metadata: dict[str, str],
        coupon_code: str | None = None,
    ) -> CheckoutSession:
        self.received_amount = amount
        self.received_currency = currency
        self.received_success_url = success_url
        self.received_cancel_url = cancel_url
        self.received_metadata = metadata
        self.received_coupon_code = coupon_code
        return CheckoutSession(
            session_id="cs_test_123",
            checkout_url="https://pay.example.test/checkout/cs_test_123",
        )

    async def create_coupon(
        self,
        code: str,
        percent_off: int,
        max_redemptions: int = 1,
    ) -> str:
        self.received_coupon = (code, percent_off, max_redemptions)
        return "coupon_123"

    async def verify_webhook(
        self,
        payload: bytes,
        signature: str,
    ) -> PaymentIntent:
        self.received_payload = payload
        self.received_signature = signature
        return PaymentIntent(
            payment_id="pi_123",
            amount=Decimal("19.99"),
            currency="eur",
            metadata={"user_id": str(uuid4())},
        )


class TestCreateCheckoutSessionRoute:
    def test_creates_checkout_session_for_authenticated_user(self) -> None:
        gateway = _PaymentGatewayStub()
        authenticated_user_id = uuid4()

        response = asyncio.run(
            create_checkout_session(
                authenticated_user_id=authenticated_user_id,
                body=CreateCheckoutSessionRequest(
                    amount=Decimal("19.99"),
                    currency="EUR",
                    success_url="https://app.example.test/payment/success",
                    cancel_url="https://app.example.test/payment/cancel",
                    metadata={"plan": "pro"},
                    coupon_code="WELCOME",
                ),
                gateway=cast(PaymentGateway, gateway),
            )
        )

        assert response.session_id == "cs_test_123"
        assert response.checkout_url == "https://pay.example.test/checkout/cs_test_123"
        assert gateway.received_amount == Decimal("19.99")
        assert gateway.received_currency == "eur"
        assert (
            gateway.received_success_url == "https://app.example.test/payment/success"
        )
        assert gateway.received_cancel_url == "https://app.example.test/payment/cancel"
        assert gateway.received_metadata == {
            "plan": "pro",
            "user_id": str(authenticated_user_id),
        }
        assert gateway.received_coupon_code == "WELCOME"


class TestCreateCouponRoute:
    def test_creates_coupon(self) -> None:
        gateway = _PaymentGatewayStub()

        response = asyncio.run(
            create_coupon(
                authenticated_user_id=uuid4(),
                body=CreateCouponRequest(
                    code="WELCOME",
                    percent_off=25,
                    max_redemptions=10,
                ),
                gateway=cast(PaymentGateway, gateway),
            )
        )

        assert response.coupon_id == "coupon_123"
        assert gateway.received_coupon == ("WELCOME", 25, 10)


class TestVerifyWebhookRoute:
    def test_verifies_webhook_with_stripe_signature(self) -> None:
        gateway = _PaymentGatewayStub()

        response = asyncio.run(
            verify_webhook(
                request=_request_with_body(b'{"id":"evt_123"}'),
                gateway=cast(PaymentGateway, gateway),
                stripe_signature="t=123,v1=abc",
            )
        )

        assert response.payment_id == "pi_123"
        assert response.amount == Decimal("19.99")
        assert gateway.received_payload == b'{"id":"evt_123"}'
        assert gateway.received_signature == "t=123,v1=abc"

    def test_rejects_webhook_without_signature(self) -> None:
        gateway = _PaymentGatewayStub()

        with pytest.raises(PaymentWebhookVerificationError):
            asyncio.run(
                verify_webhook(
                    request=_request_with_body(b"{}"),
                    gateway=cast(PaymentGateway, gateway),
                    stripe_signature=None,
                )
            )


def _request_with_body(body: bytes) -> Request:
    async def receive() -> dict[str, object]:
        return {
            "type": "http.request",
            "body": body,
            "more_body": False,
        }

    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/payments/webhook",
            "headers": [],
            "query_string": b"",
        },
        receive,
    )
