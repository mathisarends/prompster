from dishka import Provider, Scope, provide

from backend.infrastructure.email import ResendEmailSender, ResendEmailSettings
from backend.shared.email import EmailSender


class EmailProvider(Provider):
    @provide(scope=Scope.APP)
    def resend_email_settings(self) -> ResendEmailSettings:
        return ResendEmailSettings()

    @provide(scope=Scope.APP)
    def email_sender(self, settings: ResendEmailSettings) -> EmailSender:
        return ResendEmailSender(settings=settings)
