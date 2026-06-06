from backend.presentation.feature import Feature

from .infrastructure.di import PaymentProvider
from .presentation import payment_router, register_payment_exception_handlers

feature = Feature(
    name="payment",
    routers=[payment_router],
    providers=[PaymentProvider],
    register_exception_handlers=register_payment_exception_handlers,
)

__all__ = ["feature"]
