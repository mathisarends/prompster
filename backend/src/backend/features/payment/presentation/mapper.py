from backend.features.payment.application import CheckoutSession, PaymentIntent
from backend.features.payment.presentation.schemas import (
    CheckoutSessionResponse,
    PaymentIntentResponse,
)


def to_checkout_session_response(
    checkout_session: CheckoutSession,
) -> CheckoutSessionResponse:
    return CheckoutSessionResponse(
        session_id=checkout_session.session_id,
        checkout_url=checkout_session.checkout_url,
    )


def to_payment_intent_response(payment_intent: PaymentIntent) -> PaymentIntentResponse:
    return PaymentIntentResponse(
        payment_id=payment_intent.payment_id,
        amount=payment_intent.amount,
        currency=payment_intent.currency,
        metadata=payment_intent.metadata,
    )
