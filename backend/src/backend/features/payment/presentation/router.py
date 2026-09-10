from backend.features.auth.presentation.dependencies import AuthenticatedUserId
from backend.features.auth.presentation.exceptions import (
    AUTHENTICATION_REQUIRED_ERROR,
)
from backend.features.payment.application import (
    PaymentGateway,
    PaymentWebhookVerificationError,
)
from backend.features.payment.presentation.exceptions import (
    PAYMENT_ERRORS,
    PAYMENT_GATEWAY_ERROR,
    PAYMENT_WEBHOOK_VERIFICATION_ERROR,
)
from backend.features.payment.presentation.mapper import (
    to_checkout_session_response,
    to_payment_intent_response,
)
from backend.features.payment.presentation.schemas import (
    CheckoutSessionResponse,
    CouponResponse,
    CreateCheckoutSessionRequest,
    CreateCouponRequest,
    PaymentIntentResponse,
)
from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Header, Request, status

payment_router = APIRouter(
    route_class=DishkaRoute,
    prefix="/payments",
    tags=["payments"],
)


@payment_router.post(
    "/checkout-sessions",
    response_model=CheckoutSessionResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_payment_checkout_session",
    responses=PAYMENT_ERRORS.responses(
        AUTHENTICATION_REQUIRED_ERROR,
        PAYMENT_GATEWAY_ERROR,
    ),
)
async def create_checkout_session(
    authenticated_user_id: AuthenticatedUserId,
    body: CreateCheckoutSessionRequest,
    gateway: FromDishka[PaymentGateway],
) -> CheckoutSessionResponse:
    metadata = {
        **body.metadata,
        "user_id": str(authenticated_user_id),
    }
    session = await gateway.create_checkout_session(
        amount=body.amount,
        currency=body.currency.lower(),
        success_url=str(body.success_url),
        cancel_url=str(body.cancel_url),
        metadata=metadata,
        coupon_code=body.coupon_code,
    )
    return to_checkout_session_response(session)


@payment_router.post(
    "/coupons",
    response_model=CouponResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_payment_coupon",
    responses=PAYMENT_ERRORS.responses(
        AUTHENTICATION_REQUIRED_ERROR,
        PAYMENT_GATEWAY_ERROR,
    ),
)
async def create_coupon(
    authenticated_user_id: AuthenticatedUserId,
    body: CreateCouponRequest,
    gateway: FromDishka[PaymentGateway],
) -> CouponResponse:
    del authenticated_user_id
    coupon_id = await gateway.create_coupon(
        code=body.code,
        percent_off=body.percent_off,
        max_redemptions=body.max_redemptions,
    )
    return CouponResponse(coupon_id=coupon_id)


@payment_router.post(
    "/webhook",
    response_model=PaymentIntentResponse,
    status_code=status.HTTP_200_OK,
    operation_id="verify_payment_webhook",
    responses=PAYMENT_ERRORS.responses(PAYMENT_WEBHOOK_VERIFICATION_ERROR),
)
async def verify_webhook(
    request: Request,
    gateway: FromDishka[PaymentGateway],
    stripe_signature: str | None = Header(
        default=None,
        alias="Stripe-Signature",
        min_length=1,
    ),
) -> PaymentIntentResponse:
    signature = stripe_signature or request.headers.get("Payment-Signature")
    if not signature:
        raise PaymentWebhookVerificationError

    intent = await gateway.verify_webhook(
        payload=await request.body(),
        signature=signature,
    )
    return to_payment_intent_response(intent)
