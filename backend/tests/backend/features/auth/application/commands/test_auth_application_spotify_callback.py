import asyncio
from uuid import UUID, uuid4

from backend.features.auth.application.commands.auth_signup_notifier import (
    AuthSignupNotifier,
)
from backend.features.auth.application.commands.spotify_oauth_flow import (
    SpotifyOAuthFlow,
)
from backend.features.auth.application.ports import TokenIssuer
from backend.features.auth.application.schemas import (
    AuthSession,
    SpotifyLoginCallbackResult,
    TokenPayload,
    TokenType,
)
from backend.features.oauth_connections.application.ports import SpotifyOAuthProvider
from backend.features.oauth_connections.application.schemas import (
    SpotifyTokens,
    SpotifyUserProfile,
)
from backend.features.user.domain import (
    AuthIdentity,
    AuthProvider,
    User,
    UserRepository,
)
from backend.shared.email import EmailMessage, EmailSender


class _UserRepositoryStub(UserRepository):
    def __init__(self, *, existing_identity_user: User | None = None) -> None:
        self._existing_identity_user = existing_identity_user
        self.last_email_lookup: str | None = None
        self.created_user: User | None = None
        self.created_auth_identity: AuthIdentity | None = None
        self.updated_user: User | None = None

    async def get_by_id(self, *, user_id: UUID) -> User | None:
        return None

    async def delete_by_id(self, *, user_id: UUID) -> bool:
        return False

    async def count_sessions_for_user(self, *, user_id: UUID) -> int:
        return 0

    async def get_by_email(self, *, email: str) -> User | None:
        self.last_email_lookup = email
        return None

    async def get_by_auth_identity(
        self,
        *,
        provider: AuthProvider,
        subject: str,
    ) -> User | None:
        return self._existing_identity_user

    async def create(self, *, user: User) -> User:
        self.created_user = user
        self._existing_identity_user = user
        return user

    async def update(self, *, user: User) -> User:
        self.updated_user = user
        self._existing_identity_user = user
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
        return user


class _SpotifyOAuthProviderStub(SpotifyOAuthProvider):
    def __init__(self, *, tokens: SpotifyTokens, profile: SpotifyUserProfile) -> None:
        self._tokens = tokens
        self._profile = profile

    def build_authorization_url(self, *, state: str) -> str:
        return f"https://accounts.spotify.com/authorize?state={state}"

    async def exchange_code_for_tokens(
        self, *, authorization_code: str
    ) -> SpotifyTokens:
        return self._tokens

    async def fetch_spotify_user_profile(
        self, *, access_token: str
    ) -> SpotifyUserProfile:
        return self._profile

    async def refresh_access_token(self, *, refresh_token: str) -> SpotifyTokens:
        raise AssertionError(
            "refresh_access_token is not used in Spotify login callback"
        )


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
        raise AssertionError("validate is not used in Spotify login callback tests")


class _SpotifyConnectionServiceStub:
    def __init__(self) -> None:
        self.received_user_id: UUID | None = None

    async def upsert_from_tokens(
        self,
        *,
        user_id: UUID,
        tokens: SpotifyTokens,
        profile: SpotifyUserProfile,
    ) -> None:
        self.received_user_id = user_id


class _EmailSenderStub(EmailSender):
    def __init__(self) -> None:
        self.sent_messages: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> None:
        self.sent_messages.append(message)


def _signup_notifier(
    *,
    email_sender: EmailSender | None = None,
    send_welcome_email: bool = True,
) -> AuthSignupNotifier:
    return AuthSignupNotifier(
        email_sender=email_sender or _EmailSenderStub(),
        send_welcome_email=send_welcome_email,
    )


class TestSpotifyOAuthFlowCallback:
    def test_creates_new_user_and_sends_welcome_email(self) -> None:
        expected_session = AuthSession(
            access_token="access-1", refresh_token="refresh-1"
        )
        tokens = SpotifyTokens(
            access_token="spotify-access-token",
            refresh_token="spotify-refresh-token",
            expires_in=3600,
            scope="user-read-email",
            token_type="Bearer",
        )
        profile = SpotifyUserProfile(
            spotify_user_id="spotify-user-1",
            is_premium=True,
            email="  NewUser@Example.com  ",
            display_name="   ",
        )
        repository = _UserRepositoryStub()
        provider = _SpotifyOAuthProviderStub(tokens=tokens, profile=profile)
        issuer = _TokenIssuerStub(expected_session)
        connection_service = _SpotifyConnectionServiceStub()
        email_sender = _EmailSenderStub()
        handler = SpotifyOAuthFlow(
            user_repository=repository,
            spotify_oauth_client=provider,
            token_issuer=issuer,
            connection_service=connection_service,
            signup_notifier=_signup_notifier(email_sender=email_sender),
        )

        result = asyncio.run(
            handler.callback(
                code="code-1",
                state="state-1",
                error=None,
                expected_oauth_state="state-1",
            )
        )

        assert result == SpotifyLoginCallbackResult.success(session=expected_session)
        assert repository.created_user is not None
        assert repository.created_user.email == "newuser@example.com"
        assert repository.created_user.name == "newuser"
        assert connection_service.received_user_id == repository.created_user.id
        assert len(email_sender.sent_messages) == 1
        assert email_sender.sent_messages[0].to == "newuser@example.com"
        assert "Willkommen bei Prompster" in email_sender.sent_messages[0].subject

    def test_creates_new_user_without_welcome_email_when_toggle_disabled(self) -> None:
        expected_session = AuthSession(
            access_token="access-1", refresh_token="refresh-1"
        )
        tokens = SpotifyTokens(
            access_token="spotify-access-token",
            refresh_token="spotify-refresh-token",
            expires_in=3600,
            scope="user-read-email",
            token_type="Bearer",
        )
        profile = SpotifyUserProfile(
            spotify_user_id="spotify-user-1",
            is_premium=True,
            email="  NewUser@Example.com  ",
            display_name="   ",
        )
        repository = _UserRepositoryStub()
        provider = _SpotifyOAuthProviderStub(tokens=tokens, profile=profile)
        issuer = _TokenIssuerStub(expected_session)
        connection_service = _SpotifyConnectionServiceStub()
        email_sender = _EmailSenderStub()
        handler = SpotifyOAuthFlow(
            user_repository=repository,
            spotify_oauth_client=provider,
            token_issuer=issuer,
            connection_service=connection_service,
            signup_notifier=_signup_notifier(
                email_sender=email_sender,
                send_welcome_email=False,
            ),
        )

        result = asyncio.run(
            handler.callback(
                code="code-1",
                state="state-1",
                error=None,
                expected_oauth_state="state-1",
            )
        )

        assert result == SpotifyLoginCallbackResult.success(session=expected_session)
        assert repository.created_user is not None
        assert connection_service.received_user_id == repository.created_user.id
        assert email_sender.sent_messages == []

    def test_existing_user_does_not_receive_welcome_email(self) -> None:
        existing_user = User(
            name="Mathis",
            email="mathis@example.com",
            id=uuid4(),
        )
        expected_session = AuthSession(
            access_token="access-2", refresh_token="refresh-2"
        )
        tokens = SpotifyTokens(
            access_token="spotify-access-token",
            refresh_token="spotify-refresh-token",
            expires_in=3600,
            scope="user-read-email",
            token_type="Bearer",
        )
        profile = SpotifyUserProfile(
            spotify_user_id="spotify-user-1",
            is_premium=True,
            email="mathis@example.com",
            display_name="Mathis",
        )
        repository = _UserRepositoryStub(existing_identity_user=existing_user)
        provider = _SpotifyOAuthProviderStub(tokens=tokens, profile=profile)
        issuer = _TokenIssuerStub(expected_session)
        connection_service = _SpotifyConnectionServiceStub()
        email_sender = _EmailSenderStub()
        handler = SpotifyOAuthFlow(
            user_repository=repository,
            spotify_oauth_client=provider,
            token_issuer=issuer,
            connection_service=connection_service,
            signup_notifier=_signup_notifier(email_sender=email_sender),
        )

        result = asyncio.run(
            handler.callback(
                code="code-1",
                state="state-1",
                error=None,
                expected_oauth_state="state-1",
            )
        )

        assert result == SpotifyLoginCallbackResult.success(session=expected_session)
        assert repository.created_user is None
        assert issuer.received_user_id == existing_user.id
        assert connection_service.received_user_id == existing_user.id
        assert email_sender.sent_messages == []
