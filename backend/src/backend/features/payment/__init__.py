from backend.presentation.feature import api_feature

from .infrastructure.di import PaymentProvider
from .presentation import PAYMENT_ERRORS, payment_router

feature = api_feature(
    routers=[payment_router],
    providers=[PaymentProvider],
    errors=PAYMENT_ERRORS,
)

__all__ = ["feature"]
