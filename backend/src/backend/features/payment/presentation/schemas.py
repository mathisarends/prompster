from decimal import Decimal

from pydantic import AnyHttpUrl, Field

from backend.presentation.schema import Schema


class CreateCheckoutSessionRequest(Schema):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3)
    success_url: AnyHttpUrl
    cancel_url: AnyHttpUrl
    metadata: dict[str, str] = Field(default_factory=dict, max_length=50)
    coupon_code: str | None = Field(default=None, min_length=1, max_length=128)


class CheckoutSessionResponse(Schema):
    session_id: str
    checkout_url: str


class CreateCouponRequest(Schema):
    code: str = Field(min_length=1, max_length=128)
    percent_off: int = Field(ge=1, le=100)
    max_redemptions: int = Field(default=1, ge=1)


class CouponResponse(Schema):
    coupon_id: str


class PaymentIntentResponse(Schema):
    payment_id: str
    amount: Decimal
    currency: str
    metadata: dict[str, str]
