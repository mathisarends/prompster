import asyncio
from uuid import UUID, uuid4

from backend.features.auth.application.commands.google_oauth_flow import (
    GoogleOAuthFlow,
)
from backend.features.auth.application.ports import GoogleOAuthProvider, TokenIssuer
from backend.features.auth.application.schemas import (
    AuthSession,
    GoogleCallbackResult,
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


class _UserRepositoryStub(UserRepository):
    def __init__(
        self,
        *,
        existing_identity_user: User | None = None,
        existing_email_user: User | None = None,
    ) -> None:
        self._existing_identity_user = existing_identity_user
        self._existing_email_user = existing_email_user
        self.last_email_lookup: str | None = None
        self.last_auth_identity_lookup: tuple[AuthProvider, str] | None = None
        self.created_user: User | None = None
        self.created_auth_identity: AuthIdentity | None = None

    async def get_by_id(self, *, user_id: UUID) -> User | None:
        return None

    async def get_by_email(self, *, email: str) -> User | None:
        self.last_email_lookup = email
        return self._existing_email_user

    async def get_by_auth_identity(
        self,
        *,
        provider: AuthProvider,
        subject: str,
    ) -> User | None:
        self.last_auth_identity_lookup = (provider, subject)
        return self._existing_identity_user

    async def create(self, *, user: User) -> User:
        self.created_user = user
        self._existing_email_user = user
        return user

    async def create_with_auth_identity(
        self,
        *,
        user: User,
        auth_identity: AuthIdentity,
    ) -> User:
        self.created_user = user
        self.created_auth_identity = auth_identity
        self._existing_identity_user = user
        self._existing_email_user = user
        return user


class _GoogleOAuthProviderStub(GoogleOAuthProvider):
    def __init__(
        self,
        *,
        identity: GoogleIdentity | None = None,
        exchange_error: Exception | None = None,
    ) -> None:
        self._identity = identity
        self._exchange_error = exchange_error
        self.received_authorization_code: str | None = None

    def build_authorization_url(self, *, state: str) -> str:
        return f"https://example.com/auth?state={state}"

    async def exchange_code_for_identity(
        self,
        *,
        authorization_code: str,
    ) -> GoogleIdentity:
        self.received_authorization_code = authorization_code
        if self._exchange_error is not None:
            raise self._exchange_error
        assert self._identity is not None
        return self._identity


class _TokenIssuerStub(TokenIssuer):
    def __init__(self, session: AuthSession) -> None:
        self._session = session
        self.received_user_id: UUID | None = None

    def create_session(self, user_id: UUID) -> AuthSession:
        self.received_user_id = user_id
        return self._session

    def validate(
        self,
        token: str,
        expected_type: TokenType = TokenType.ACCESS,
    ) -> TokenPayload:
        raise AssertionError("validate is not used in Google OAuth flow tests")


class TestGoogleOAuthFlowCallback:
    def test_handle_callback_returns_invalid_credentials_for_missing_expected_state(
        self,
    ) -> None:
        repository = _UserRepositoryStub()
        provider = _GoogleOAuthProviderStub()
        issuer = _TokenIssuerStub(AuthSession(access_token="a", refresh_token="r"))
        handler = GoogleOAuthFlow(repository, provider, issuer)

        result = asyncio.run(
            handler.callback(
                code="code-1",
                state="state-1",
                error=None,
                expected_oauth_state=None,
            )
        )

        assert result == GoogleCallbackResult.error(reason="invalid_credentials")

    def test_handle_callback_returns_invalid_credentials_for_mismatched_state(
        self,
    ) -> None:
        repository = _UserRepositoryStub()
        provider = _GoogleOAuthProviderStub()
        issuer = _TokenIssuerStub(AuthSession(access_token="a", refresh_token="r"))
        handler = GoogleOAuthFlow(repository, provider, issuer)

        result = asyncio.run(
            handler.callback(
                code="code-1",
                state="state-1",
                error=None,
                expected_oauth_state="state-2",
            )
        )

        assert result == GoogleCallbackResult.error(reason="invalid_credentials")

    def test_handle_callback_returns_invalid_credentials_for_invalid_code(self) -> None:
        repository = _UserRepositoryStub()
        provider = _GoogleOAuthProviderStub(exchange_error=ValueError("invalid code"))
        issuer = _TokenIssuerStub(AuthSession(access_token="a", refresh_token="r"))
        handler = GoogleOAuthFlow(repository, provider, issuer)

        result = asyncio.run(
            handler.callback(
                code="code-1",
                state="state-1",
                error=None,
                expected_oauth_state="state-1",
            )
        )

        assert result == GoogleCallbackResult.error(reason="invalid_credentials")

    def test_handle_callback_returns_invalid_credentials_for_unverified_email(
        self,
    ) -> None:
        identity = GoogleIdentity(
            subject="google-sub-1",
            email="mathis@example.com",
            email_verified=False,
        )
        repository = _UserRepositoryStub()
        provider = _GoogleOAuthProviderStub(identity=identity)
        issuer = _TokenIssuerStub(AuthSession(access_token="a", refresh_token="r"))
        handler = GoogleOAuthFlow(repository, provider, issuer)

        result = asyncio.run(
            handler.callback(
                code="code-1",
                state="state-1",
                error=None,
                expected_oauth_state="state-1",
            )
        )

        assert result == GoogleCallbackResult.error(reason="invalid_credentials")

    def test_handle_callback_creates_user_when_missing_and_returns_session(
        self,
    ) -> None:
        identity = GoogleIdentity(
            subject="google-sub-1",
            email="  NewUser@Example.com  ",
            name="   ",
            email_verified=True,
        )
        expected_session = AuthSession(
            access_token="access-1", refresh_token="refresh-1"
        )
        repository = _UserRepositoryStub()
        provider = _GoogleOAuthProviderStub(identity=identity)
        issuer = _TokenIssuerStub(expected_session)
        handler = GoogleOAuthFlow(repository, provider, issuer)

        result = asyncio.run(
            handler.callback(
                code="code-1",
                state="state-1",
                error=None,
                expected_oauth_state="state-1",
            )
        )

        assert result == GoogleCallbackResult.success(session=expected_session)
        assert repository.last_email_lookup == "newuser@example.com"
        assert repository.last_auth_identity_lookup == (
            AuthProvider.GOOGLE,
            "google-sub-1",
        )
        assert repository.created_user is not None
        assert repository.created_user.email == "newuser@example.com"
        assert repository.created_user.name == "newuser"
        assert repository.created_auth_identity is not None
        assert repository.created_auth_identity.user_id == repository.created_user.id
        assert repository.created_auth_identity.provider == AuthProvider.GOOGLE
        assert repository.created_auth_identity.subject == "google-sub-1"
        assert issuer.received_user_id == repository.created_user.id

    def test_handle_callback_returns_invalid_credentials_for_email_identity_mismatch(
        self,
    ) -> None:
        existing_user = User(
            name="Mathis",
            email="mathis@example.com",
            id=uuid4(),
        )
        identity = GoogleIdentity(
            subject="google-sub-new",
            email="mathis@example.com",
            name="Mathis",
            email_verified=True,
        )
        repository = _UserRepositoryStub(existing_email_user=existing_user)
        provider = _GoogleOAuthProviderStub(identity=identity)
        issuer = _TokenIssuerStub(AuthSession(access_token="a", refresh_token="r"))
        handler = GoogleOAuthFlow(repository, provider, issuer)

        result = asyncio.run(
            handler.callback(
                code="code-1",
                state="state-1",
                error=None,
                expected_oauth_state="state-1",
            )
        )

        assert result == GoogleCallbackResult.error(reason="invalid_credentials")

    def test_handle_callback_returns_session_for_existing_matching_user(self) -> None:
        existing_user = User(
            name="Mathis",
            email="mathis@example.com",
            id=uuid4(),
        )
        identity = GoogleIdentity(
            subject="google-sub-1",
            email="  mathis@example.com ",
            name="Mathis",
            email_verified=True,
        )
        expected_session = AuthSession(
            access_token="access-2", refresh_token="refresh-2"
        )
        repository = _UserRepositoryStub(existing_identity_user=existing_user)
        provider = _GoogleOAuthProviderStub(identity=identity)
        issuer = _TokenIssuerStub(expected_session)
        handler = GoogleOAuthFlow(repository, provider, issuer)

        result = asyncio.run(
            handler.callback(
                code="code-1",
                state="state-1",
                error=None,
                expected_oauth_state="state-1",
            )
        )

        assert result == GoogleCallbackResult.success(session=expected_session)
        assert repository.created_user is None
        assert repository.last_email_lookup is None
        assert repository.last_auth_identity_lookup == (
            AuthProvider.GOOGLE,
            "google-sub-1",
        )
        assert issuer.received_user_id == existing_user.id

    def test_handle_callback_returns_provider_error_reason_without_exchange(
        self,
    ) -> None:
        repository = _UserRepositoryStub()
        provider = _GoogleOAuthProviderStub()
        issuer = _TokenIssuerStub(AuthSession(access_token="a", refresh_token="r"))
        handler = GoogleOAuthFlow(repository, provider, issuer)

        result = asyncio.run(
            handler.callback(
                code=None,
                state="state-1",
                error="access_denied",
                expected_oauth_state="state-1",
            )
        )

        assert result == GoogleCallbackResult.error(reason="access_denied")
        assert provider.received_authorization_code is None

    def test_handle_callback_returns_missing_code_without_exchange(self) -> None:
        repository = _UserRepositoryStub()
        provider = _GoogleOAuthProviderStub()
        issuer = _TokenIssuerStub(AuthSession(access_token="a", refresh_token="r"))
        handler = GoogleOAuthFlow(repository, provider, issuer)

        result = asyncio.run(
            handler.callback(
                code=None,
                state="state-1",
                error=None,
                expected_oauth_state="state-1",
            )
        )

        assert result == GoogleCallbackResult.error(reason="missing_code")
        assert provider.received_authorization_code is None
