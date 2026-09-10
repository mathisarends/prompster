import asyncio
from uuid import UUID

from backend.features.auth.application.ports import TokenIssuer
from backend.features.auth.application.schemas import (
    AuthSession,
    TokenPayload,
    TokenType,
)
from backend.features.auth.application.spotify_oauth_flow import SpotifyOAuthFlow
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


class _Repository(UserRepository):
    def __init__(self) -> None:
        self.user: User | None = None
        self.identity: AuthIdentity | None = None

    async def get_by_id(self, *, user_id: UUID) -> User | None:
        return self.user

    async def delete_by_id(self, *, user_id: UUID) -> bool:
        return False

    async def count_sessions_for_user(self, *, user_id: UUID) -> int:
        return 0

    async def get_by_auth_identity(
        self, *, provider: AuthProvider, subject: str
    ) -> User | None:
        return self.user if self.identity and self.identity.subject == subject else None

    async def create(self, *, user: User) -> User:
        self.user = user
        return user

    async def update(self, *, user: User) -> User:
        self.user = user
        return user

    async def create_with_auth_identity(
        self, *, user: User, auth_identity: AuthIdentity
    ) -> User:
        self.user = user
        self.identity = auth_identity
        return user


class _SpotifyProvider(SpotifyOAuthProvider):
    def build_authorization_url(self, *, state: str) -> str:
        return f"https://example.invalid/auth?state={state}"

    async def exchange_code_for_tokens(
        self, *, authorization_code: str
    ) -> SpotifyTokens:
        return SpotifyTokens(
            access_token="access",
            refresh_token="refresh",
            expires_in=3600,
            scope="user-read-private",
            token_type="Bearer",
        )

    async def fetch_spotify_user_profile(
        self, *, access_token: str
    ) -> SpotifyUserProfile:
        return SpotifyUserProfile(
            spotify_user_id="spotify-user",
            is_premium=True,
            display_name="Mathis",
        )

    async def refresh_access_token(self, *, refresh_token: str) -> SpotifyTokens:
        raise AssertionError("Not used")


class _TokenIssuer(TokenIssuer):
    def create_session(self, user_id: UUID) -> AuthSession:
        return AuthSession(access_token=str(user_id), refresh_token="refresh")

    def validate(
        self, token: str, expected_type: TokenType = TokenType.ACCESS
    ) -> TokenPayload:
        raise AssertionError("Not used")


class _ConnectionService:
    async def upsert_from_tokens(
        self,
        *,
        user_id: UUID,
        tokens: SpotifyTokens,
        profile: SpotifyUserProfile,
    ) -> None:
        return None


def test_spotify_callback_creates_a_user_without_a_contact_address() -> None:
    repository = _Repository()
    flow = SpotifyOAuthFlow(
        repository,
        _SpotifyProvider(),
        _TokenIssuer(),
        _ConnectionService(),  # type: ignore[arg-type]
    )

    result = asyncio.run(
        flow.callback(
            code="code",
            state="state",
            error=None,
            expected_oauth_state="state",
        )
    )

    assert result.succeeded is True
    assert repository.user is not None
    assert repository.user.name == "Mathis"
    assert repository.identity is not None
    assert repository.identity.provider == AuthProvider.SPOTIFY
