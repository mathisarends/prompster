import hashlib
import hmac
import json
import time
from decimal import Decimal
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError

from backend.features.payment.application import (
    CheckoutSession,
    PaymentGateway,
    PaymentGatewayError,
    PaymentIntent,
    PaymentWebhookVerificationError,
)
from backend.features.payment.infrastructure.settings import StripePaymentSettings

_ZERO_DECIMAL_CURRENCIES = frozenset(
    {
        "bif",
        "clp",
        "djf",
        "gnf",
        "jpy",
        "kmf",
        "krw",
        "mga",
        "pyg",
        "rwf",
        "ugx",
        "vnd",
        "vuv",
        "xaf",
        "xof",
        "xpf",
    }
)


class _CheckoutSessionResponse(BaseModel):
    id: str = Field(min_length=1)
    url: str = Field(min_length=1)


class StripePaymentGateway(PaymentGateway):
    def __init__(self, settings: StripePaymentSettings) -> None:
        self._settings = settings

    async def create_checkout_session(
        self,
        amount: Decimal,
        currency: str,
        success_url: str,
        cancel_url: str,
        metadata: dict[str, str],
        coupon_code: str | None = None,
    ) -> CheckoutSession:
        normalized_currency = _normalize_currency(currency)
        form = _flatten_form(
            {
                "mode": "payment",
                "success_url": success_url,
                "cancel_url": cancel_url,
                "line_items": [
                    {
                        "price_data": {
                            "currency": normalized_currency,
                            "unit_amount": _to_minor_units(
                                amount,
                                currency=normalized_currency,
                            ),
                            "product_data": {
                                "name": self._settings.checkout_product_name,
                            },
                        },
                        "quantity": 1,
                    }
                ],
                "metadata": metadata,
                "payment_intent_data": {
                    "metadata": metadata,
                },
                **(
                    {"discounts": [{"coupon": coupon_code}]}
                    if coupon_code is not None
                    else {}
                ),
            }
        )

        payload = await self._post("/v1/checkout/sessions", form)
        try:
            session = _CheckoutSessionResponse.model_validate(payload)
        except ValidationError as exc:
            raise PaymentGatewayError(
                "Stripe checkout session payload is invalid"
            ) from exc

        return CheckoutSession(
            session_id=session.id,
            checkout_url=session.url,
        )

    async def create_coupon(
        self,
        code: str,
        percent_off: int,
        max_redemptions: int = 1,
    ) -> str:
        normalized_code = code.strip()
        if not normalized_code:
            raise ValueError("Coupon code must not be empty")

        payload = await self._post(
            "/v1/coupons",
            {
                "id": normalized_code,
                "percent_off": str(percent_off),
                "duration": "once",
                "max_redemptions": str(max_redemptions),
            },
        )
        coupon_id = str(payload.get("id", "")).strip()
        if not coupon_id:
            raise PaymentGatewayError("Stripe coupon payload is invalid")
        return coupon_id

    async def verify_webhook(
        self,
        payload: bytes,
        signature: str,
    ) -> PaymentIntent:
        event = self._verify_signature(payload=payload, signature=signature)
        return _to_payment_intent(event)

    async def _post(self, path: str, data: dict[str, str]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self._settings.api_base_url}{path}",
                data=data,
                headers={
                    "Authorization": f"Bearer {self._settings.secret_key}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )

        if response.status_code >= 400:
            raise PaymentGatewayError(_stripe_error_detail(response))

        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise PaymentGatewayError("Stripe response is not valid JSON") from exc

        if not isinstance(payload, dict):
            raise PaymentGatewayError("Stripe response payload is invalid")
        return payload

    def _verify_signature(self, *, payload: bytes, signature: str) -> dict[str, Any]:
        parts = _parse_stripe_signature(signature)
        timestamp = parts.get("t")
        signatures = parts.get("v1", [])
        if timestamp is None or not signatures:
            raise PaymentWebhookVerificationError("Stripe webhook signature is invalid")

        try:
            timestamp_value = int(timestamp[0])
        except ValueError as exc:
            raise PaymentWebhookVerificationError(
                "Stripe webhook timestamp is invalid"
            ) from exc

        if self._settings.webhook_tolerance_seconds > 0:
            age = abs(int(time.time()) - timestamp_value)
            if age > self._settings.webhook_tolerance_seconds:
                raise PaymentWebhookVerificationError(
                    "Stripe webhook timestamp expired"
                )

        signed_payload = str(timestamp_value).encode("utf-8") + b"." + payload
        expected = hmac.new(
            self._settings.webhook_secret.encode("utf-8"),
            signed_payload,
            hashlib.sha256,
        ).hexdigest()
        if not any(
            hmac.compare_digest(expected, candidate) for candidate in signatures
        ):
            raise PaymentWebhookVerificationError("Stripe webhook signature mismatch")

        try:
            event = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise PaymentWebhookVerificationError(
                "Stripe webhook payload is not valid JSON"
            ) from exc

        if not isinstance(event, dict):
            raise PaymentWebhookVerificationError("Stripe webhook payload is invalid")
        return event


def _flatten_form(payload: dict[str, Any]) -> dict[str, str]:
    flattened: dict[str, str] = {}

    def walk(prefix: str, value: Any) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                walk(f"{prefix}[{key}]", nested)
            return

        if isinstance(value, list):
            for index, nested in enumerate(value):
                walk(f"{prefix}[{index}]", nested)
            return

        flattened[prefix] = str(value)

    for key, value in payload.items():
        walk(key, value)
    return flattened


def _normalize_currency(currency: str) -> str:
    normalized = currency.strip().lower()
    if len(normalized) != 3:
        raise ValueError("Currency must be an ISO 4217 code")
    return normalized


def _to_minor_units(amount: Decimal, *, currency: str) -> int:
    exponent = 0 if currency in _ZERO_DECIMAL_CURRENCIES else 2
    multiplier = Decimal(10) ** exponent
    minor_amount = amount * multiplier
    if minor_amount != minor_amount.to_integral_value():
        raise ValueError("Amount has too many decimal places for currency")
    if minor_amount <= 0:
        raise ValueError("Amount must be greater than zero")
    return int(minor_amount)


def _from_minor_units(amount: int, *, currency: str) -> Decimal:
    exponent = 0 if currency in _ZERO_DECIMAL_CURRENCIES else 2
    return Decimal(amount) / (Decimal(10) ** exponent)


def _parse_stripe_signature(signature: str) -> dict[str, list[str]]:
    parts: dict[str, list[str]] = {}
    for item in signature.split(","):
        key, separator, value = item.partition("=")
        if not separator:
            continue
        parts.setdefault(key, []).append(value)
    return parts


def _to_payment_intent(event: dict[str, Any]) -> PaymentIntent:
    obj = _stripe_event_object(event)
    try:
        currency = _normalize_currency(str(obj.get("currency", "")))
    except ValueError as exc:
        raise PaymentWebhookVerificationError(
            "Stripe webhook currency is invalid"
        ) from exc
    amount = _stripe_amount(obj)
    payment_id = str(obj.get("payment_intent") or obj.get("id") or "").strip()
    if not payment_id:
        raise PaymentWebhookVerificationError("Stripe webhook payment id is missing")

    metadata = obj.get("metadata") or {}
    if not isinstance(metadata, dict):
        raise PaymentWebhookVerificationError("Stripe webhook metadata is invalid")

    return PaymentIntent(
        payment_id=payment_id,
        amount=_from_minor_units(amount, currency=currency),
        currency=currency,
        metadata={str(key): str(value) for key, value in metadata.items()},
    )


def _stripe_event_object(event: dict[str, Any]) -> dict[str, Any]:
    data = event.get("data")
    obj = data.get("object") if isinstance(data, dict) else None
    if not isinstance(obj, dict):
        raise PaymentWebhookVerificationError("Stripe webhook object is missing")
    return obj


def _stripe_amount(obj: dict[str, Any]) -> int:
    raw_amount = (
        obj.get("amount_received") or obj.get("amount_total") or obj.get("amount")
    )
    if not isinstance(raw_amount, int) or raw_amount <= 0:
        raise PaymentWebhookVerificationError("Stripe webhook amount is invalid")
    return raw_amount


def _stripe_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except json.JSONDecodeError:
        return "Stripe request failed"

    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            message = str(error.get("message", "")).strip()
            if message:
                return message
    return "Stripe request failed"
