from backend.features.user.domain import User
from backend.shared.email import EmailSender

from ._welcome_email import build_welcome_email


class AuthSignupNotifier:
    def __init__(
        self,
        email_sender: EmailSender,
        send_welcome_email: bool = True,
    ) -> None:
        self._email_sender = email_sender
        self._send_welcome_email = send_welcome_email

    async def notify_user_created(self, *, user: User) -> None:
        if not self._send_welcome_email:
            return

        await self._email_sender.send(build_welcome_email(user=user))
