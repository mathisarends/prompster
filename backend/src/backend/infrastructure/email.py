import asyncio

from backend.shared.email import EmailMessage, EmailSender

import resend


class ResendEmailSender(EmailSender):
    def __init__(self, api_key: str) -> None:
        resend.api_key = api_key

    async def send(self, message: EmailMessage) -> None:
        await asyncio.to_thread(
            resend.Emails.send,
            {
                "from": message.from_email,
                "to": message.to,
                "subject": message.subject,
                "html": message.html,
            },
        )
