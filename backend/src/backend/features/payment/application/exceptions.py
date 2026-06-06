class PaymentGatewayError(Exception):
    pass


class PaymentWebhookVerificationError(PaymentGatewayError):
    pass
