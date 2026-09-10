from html import escape as html_escape

from backend.features.user.domain import User
from backend.shared.email import EmailMessage


def build_welcome_email(*, user: User) -> EmailMessage:
    safe_name = html_escape(user.name.strip() or user.email.split("@", maxsplit=1)[0])
    return EmailMessage(
        to=user.email,
        subject="Willkommen bei Prompster",
        html=(
            f"<p>Hi {safe_name},</p>"
            "<p>schoen, dass du bei Prompster bist. Dein Account ist jetzt erfolgreich eingerichtet.</p>"
            "<p>Viel Spass beim Entdecken.</p>"
        ),
    )
