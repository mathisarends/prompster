from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Header, HTTPException, Request, status

from backend.features.auth.presentation.dependencies import AuthenticatedUserId
from backend.features.payment.application import PaymentGateway
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
from backend.presentation.errors import ErrorDto

payment_router = APIRouter(
    route_class=DishkaRoute,
    prefix="/payments",
    tags=["payments"],
)

_auth_errors = {
    status.HTTP_401_UNAUTHORIZED: {"model": ErrorDto},
    status.HTTP_403_FORBIDDEN: {"model": ErrorDto},
}
_bad_request = {status.HTTP_400_BAD_REQUEST: {"model": ErrorDto}}


@payment_router.post(
    "/checkout-sessions",
    response_model=CheckoutSessionResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_payment_checkout_session",
    responses=_auth_errors | _bad_request,
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
    responses=_auth_errors | _bad_request,
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
    responses=_bad_request,
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing payment webhook signature",
        )

    intent = await gateway.verify_webhook(
        payload=await request.body(),
        signature=signature,
    )
    return to_payment_intent_response(intent)
