from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class CheckoutSession:
    session_id: str
    checkout_url: str


@dataclass(frozen=True, slots=True)
class PaymentIntent:
    payment_id: str
    amount: Decimal
    currency: str
    metadata: dict[str, str]


class PaymentGateway(ABC):
    @abstractmethod
    async def create_checkout_session(
        self,
        amount: Decimal,
        currency: str,
        success_url: str,
        cancel_url: str,
        metadata: dict[str, str],
        coupon_code: str | None = None,
    ) -> CheckoutSession:
        raise NotImplementedError

    @abstractmethod
    async def create_coupon(
        self,
        code: str,
        percent_off: int,
        max_redemptions: int = 1,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    async def verify_webhook(
        self,
        payload: bytes,
        signature: str,
    ) -> PaymentIntent:
        raise NotImplementedError
