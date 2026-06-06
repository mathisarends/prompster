from dishka import Provider, Scope, provide

from backend.features.payment.application import PaymentGateway
from backend.features.payment.infrastructure.settings import StripePaymentSettings
from backend.features.payment.infrastructure.stripe_payment_gateway import (
    StripePaymentGateway,
)


class PaymentProvider(Provider):
    @provide(scope=Scope.APP)
    def stripe_payment_settings(self) -> StripePaymentSettings:
        return StripePaymentSettings()

    @provide(scope=Scope.APP)
    def provide_payment_gateway(
        self,
        settings: StripePaymentSettings,
    ) -> PaymentGateway:
        return StripePaymentGateway(settings=settings)
