from backend.presentation.feature import Feature

from .presentation import payment_router

feature = Feature(
    name="payment",
    routers=[payment_router],
)

__all__ = ["feature"]
