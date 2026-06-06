import asyncio
import hashlib
import hmac
import json
import time
from decimal import Decimal

import pytest

from backend.features.payment.application import PaymentWebhookVerificationError
from backend.features.payment.infrastructure.settings import StripePaymentSettings
from backend.features.payment.infrastructure.stripe_payment_gateway import (
    StripePaymentGateway,
)


class _ResponseStub:
    def __init__(self, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload


class _AsyncClientStub:
    response = _ResponseStub(
        status_code=200,
        payload={
            "id": "cs_test_123",
            "url": "https://checkout.stripe.test/cs_test_123",
        },
    )
    requests: list[dict] = []

    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self) -> "_AsyncClientStub":
        return self

    async def __aexit__(self, *args) -> None:
        pass

    async def post(self, url: str, data: dict, headers: dict) -> _ResponseStub:
        self.requests.append(
            {
                "url": url,
                "data": data,
                "headers": headers,
            }
        )
        return self.response


@pytest.fixture(autouse=True)
def reset_async_client_stub() -> None:
    _AsyncClientStub.response = _ResponseStub(
        status_code=200,
        payload={
            "id": "cs_test_123",
            "url": "https://checkout.stripe.test/cs_test_123",
        },
    )
    _AsyncClientStub.requests = []


class TestStripeCreateCheckoutSession:
    def test_posts_checkout_session_to_stripe(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("httpx.AsyncClient", _AsyncClientStub)
        gateway = _gateway()

        response = asyncio.run(
            gateway.create_checkout_session(
                amount=Decimal("19.99"),
                currency="EUR",
                success_url="https://app.example.test/success",
                cancel_url="https://app.example.test/cancel",
                metadata={"user_id": "user-123"},
                coupon_code="WELCOME",
            )
        )

        assert response.session_id == "cs_test_123"
        assert response.checkout_url == "https://checkout.stripe.test/cs_test_123"
        request = _AsyncClientStub.requests[0]
        assert request["url"] == "https://stripe.example.test/v1/checkout/sessions"
        assert request["headers"]["Authorization"] == "Bearer sk_test_123"
        assert request["data"]["mode"] == "payment"
        assert request["data"]["line_items[0][price_data][currency]"] == "eur"
        assert request["data"]["line_items[0][price_data][unit_amount]"] == "1999"
        assert request["data"]["metadata[user_id]"] == "user-123"
        assert request["data"]["payment_intent_data[metadata][user_id]"] == "user-123"
        assert request["data"]["discounts[0][coupon]"] == "WELCOME"


class TestStripeCreateCoupon:
    def test_posts_coupon_to_stripe(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("httpx.AsyncClient", _AsyncClientStub)
        _AsyncClientStub.response = _ResponseStub(200, {"id": "WELCOME"})
        gateway = _gateway()

        coupon_id = asyncio.run(
            gateway.create_coupon(
                code="WELCOME",
                percent_off=25,
                max_redemptions=10,
            )
        )

        assert coupon_id == "WELCOME"
        request = _AsyncClientStub.requests[0]
        assert request["url"] == "https://stripe.example.test/v1/coupons"
        assert request["data"] == {
            "id": "WELCOME",
            "percent_off": "25",
            "duration": "once",
            "max_redemptions": "10",
        }


class TestStripeVerifyWebhook:
    def test_verifies_signed_payment_intent_webhook(self) -> None:
        gateway = _gateway()
        payload = json.dumps(
            {
                "type": "payment_intent.succeeded",
                "data": {
                    "object": {
                        "id": "pi_123",
                        "amount_received": 1999,
                        "currency": "eur",
                        "metadata": {"user_id": "user-123"},
                    }
                },
            }
        ).encode("utf-8")
        timestamp = int(time.time())

        intent = asyncio.run(
            gateway.verify_webhook(
                payload=payload,
                signature=_signature(payload, timestamp=timestamp),
            )
        )

        assert intent.payment_id == "pi_123"
        assert intent.amount == Decimal("19.99")
        assert intent.currency == "eur"
        assert intent.metadata == {"user_id": "user-123"}

    def test_rejects_invalid_signature(self) -> None:
        gateway = _gateway()

        with pytest.raises(PaymentWebhookVerificationError):
            asyncio.run(
                gateway.verify_webhook(
                    payload=b"{}",
                    signature="t=123,v1=wrong",
                )
            )


def _gateway() -> StripePaymentGateway:
    return StripePaymentGateway(
        StripePaymentSettings(
            secret_key="sk_test_123",
            webhook_secret="whsec_123",
            api_base_url="https://stripe.example.test",
        )
    )


def _signature(payload: bytes, *, timestamp: int) -> str:
    signed_payload = str(timestamp).encode("utf-8") + b"." + payload
    digest = hmac.new(
        b"whsec_123",
        signed_payload,
        hashlib.sha256,
    ).hexdigest()
    return f"t={timestamp},v1={digest}"
