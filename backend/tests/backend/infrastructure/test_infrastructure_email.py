import asyncio

import pytest
from pydantic import ValidationError

from backend.infrastructure.email import ResendEmailSender, ResendEmailSettings
from backend.shared.email import EmailMessage


class _ResendEmailsStub:
    payload: dict[str, object] | None = None

    @staticmethod
    def send(payload: dict[str, object]) -> None:
        _ResendEmailsStub.payload = payload


class TestResendEmailSettings:
    def test_reads_api_key_from_environment(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("RESEND_API_KEY", "test-resend-key")

        settings = ResendEmailSettings(_env_file=None)

        assert settings.api_key == "test-resend-key"

    def test_rejects_blank_api_key_from_environment(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("RESEND_API_KEY", "   ")

        with pytest.raises(ValidationError, match="Resend API key is not configured"):
            ResendEmailSettings(_env_file=None)


class TestResendEmailSender:
    def test_uses_configured_default_from_email_when_message_sender_is_missing(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _ResendEmailsStub.payload = None
        monkeypatch.setattr("resend.Emails.send", _ResendEmailsStub.send)

        sender = ResendEmailSender(
            settings=ResendEmailSettings(
                api_key="resend-key",
                from_email="sender@example.com",
                _env_file=None,
            )
        )

        asyncio.run(
            sender.send(
                EmailMessage(
                    to="recipient@example.com",
                    subject="Welcome",
                    html="<p>Hello</p>",
                )
            )
        )

        assert _ResendEmailsStub.payload is not None
        assert _ResendEmailsStub.payload["from"] == "sender@example.com"
        assert _ResendEmailsStub.payload["to"] == "recipient@example.com"
