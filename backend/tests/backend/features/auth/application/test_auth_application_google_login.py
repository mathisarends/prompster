import secrets
from uuid import UUID

import pytest

from backend.features.auth.application.auth_signup_notifier import (
    AuthSignupNotifier,
)
from backend.features.auth.application.google_oauth_flow import (
    GoogleOAuthFlow,
)
from backend.features.auth.application.ports import GoogleOAuthProvider, TokenIssuer
from backend.features.auth.application.schemas import (
    AuthSession,
    GoogleAuthorizationRequest,
    GoogleIdentity,
    TokenPayload,
    TokenType,
)
from backend.features.user.domain import (
    AuthIdentity,
    AuthProvider,
    User,
    UserRepository,
)
from backend.shared.email import EmailMessage, EmailSender


class _UserRepositoryStub(UserRepository):
    async def get_by_id(self, *, user_id: UUID) -> User | None:
        raise AssertionError("Google login must not load users")

    async def delete_by_id(self, *, user_id: UUID) -> bool:
        raise AssertionError("Google login must not delete users")

    async def count_sessions_for_user(self, *, user_id: UUID) -> int:
        raise AssertionError("Google login must not count sessions")

    async def get_by_email(self, *, email: str) -> User | None:
        raise AssertionError("Google login must not query users")

    async def get_by_auth_identity(
        self,
        *,
        provider: AuthProvider,
        subject: str,
    ) -> User | None:
        raise AssertionError("Google login must not query auth identities")

    async def create(self, *, user: User) -> User:
        raise AssertionError("Google login must not create users")

    async def update(self, *, user: User) -> User:
        raise AssertionError("Google login must not update users")

    async def create_with_auth_identity(
        self,
        *,
        user: User,
        auth_identity: AuthIdentity,
    ) -> User:
        raise AssertionError("Google login must not create users")


class _TokenIssuerStub(TokenIssuer):
    def create_session(self, user_id: UUID) -> AuthSession:
        raise AssertionError("Google login must not issue tokens")

    def validate(
        self,
        token: str,
        expected_type: TokenType = TokenType.ACCESS,
    ) -> TokenPayload:
        raise AssertionError("Google login tests do not validate tokens")


class _GoogleOAuthProviderStub(GoogleOAuthProvider):
    def __init__(self) -> None:
        self.received_state: str | None = None

    def build_authorization_url(self, *, state: str) -> str:
        self.received_state = state
        return f"https://accounts.google.com/o/oauth2/auth?state={state}"

    async def exchange_code_for_identity(
        self,
        *,
        authorization_code: str,
    ) -> GoogleIdentity:
        raise AssertionError("Google login must not exchange an authorization code")


class _EmailSenderStub(EmailSender):
    async def send(self, message: EmailMessage) -> None:
        raise AssertionError("Google login must not send emails")


class TestGoogleOAuthFlowLogin:
    def test_handle_login_generates_oauth_state_and_builds_authorization_request(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(secrets, "token_urlsafe", lambda _: "state-123")
        provider = _GoogleOAuthProviderStub()
        handler = GoogleOAuthFlow(
            user_repository=_UserRepositoryStub(),
            google_oauth_provider=provider,
            token_issuer=_TokenIssuerStub(),
            signup_notifier=AuthSignupNotifier(email_sender=_EmailSenderStub()),
        )

        result = handler.login()

        assert isinstance(result, GoogleAuthorizationRequest)
        assert result.state == "state-123"
        assert result.authorization_url.endswith("state=state-123")
        assert provider.received_state == "state-123"
