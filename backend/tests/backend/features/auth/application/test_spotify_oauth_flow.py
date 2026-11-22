import asyncio
from uuid import UUID

from backend.features.auth.application.ports import SpotifyLogin, SpotifyLoginProvider
from backend.shared.authentication import (
    AuthSession,
    TokenIssuer,
    TokenPayload,
    TokenType,
)
from backend.features.auth.domain import SpotifyIdentity
from backend.features.auth.application.spotify_oauth_flow import SpotifyOAuthFlow
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


class _SpotifyLogin(SpotifyLogin):
    def __init__(self) -> None:
        self.connected_user_id: UUID | None = None

    @property
    def identity(self) -> SpotifyIdentity:
        return SpotifyIdentity(subject="spotify-user", display_name="Mathis")

    async def connect(self, *, user_id: UUID) -> None:
        self.connected_user_id = user_id


class _SpotifyLoginProvider(SpotifyLoginProvider):
    def __init__(self) -> None:
        self.login = _SpotifyLogin()

    def build_authorization_url(self, *, state: str) -> str:
        return f"https://example.invalid/auth?state={state}"

    async def authorize(self, *, authorization_code: str) -> SpotifyLogin:
        return self.login


class _TokenIssuer(TokenIssuer):
    def create_session(self, user_id: UUID) -> AuthSession:
        return AuthSession(access_token=str(user_id), refresh_token="refresh")

    def validate(
        self, token: str, expected_type: TokenType = TokenType.ACCESS
    ) -> TokenPayload:
        raise AssertionError("Not used")


def test_spotify_callback_creates_a_user_without_a_contact_address() -> None:
    repository = _Repository()
    login_provider = _SpotifyLoginProvider()
    flow = SpotifyOAuthFlow(repository, login_provider, _TokenIssuer())

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
    assert login_provider.login.connected_user_id == repository.user.id
