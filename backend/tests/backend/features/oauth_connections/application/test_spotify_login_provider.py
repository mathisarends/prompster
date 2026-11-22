import asyncio
from uuid import UUID

from backend.features.oauth_connections.application.ports import SpotifyOAuthProvider
from backend.features.oauth_connections.application.schemas import (
    SpotifyTokens,
    SpotifyUserProfile,
)
from backend.features.oauth_connections.application.spotify_login_provider import (
    SpotifyAccountLoginProvider,
)

_TOKENS = SpotifyTokens(
    access_token="access",
    refresh_token="refresh",
    expires_in=3600,
    scope="user-read-private",
    token_type="Bearer",
)
_PROFILE = SpotifyUserProfile(
    spotify_user_id="spotify-user",
    is_premium=True,
    display_name="Mathis",
    profile_image_url="https://example.invalid/me.png",
)


class _SpotifyProvider(SpotifyOAuthProvider):
    def build_authorization_url(self, *, state: str) -> str:
        return f"https://example.invalid/auth?state={state}"

    async def exchange_code_for_tokens(
        self, *, authorization_code: str
    ) -> SpotifyTokens:
        return _TOKENS

    async def fetch_spotify_user_profile(
        self, *, access_token: str
    ) -> SpotifyUserProfile:
        return _PROFILE

    async def refresh_access_token(self, *, refresh_token: str) -> SpotifyTokens:
        raise AssertionError("Not used")


class _ConnectionService:
    def __init__(self) -> None:
        self.upserted: tuple[UUID, SpotifyTokens, SpotifyUserProfile] | None = None

    async def upsert_from_tokens(
        self,
        *,
        user_id: UUID,
        tokens: SpotifyTokens,
        profile: SpotifyUserProfile,
    ) -> None:
        self.upserted = (user_id, tokens, profile)


def _provider(connections: _ConnectionService) -> SpotifyAccountLoginProvider:
    return SpotifyAccountLoginProvider(
        spotify_oauth_provider=_SpotifyProvider(),
        connection_service=connections,  # type: ignore[arg-type]
    )


def test_authorize_exposes_the_spotify_identity() -> None:
    login = asyncio.run(
        _provider(_ConnectionService()).authorize(authorization_code="c")
    )

    assert login.identity.subject == "spotify-user"
    assert login.identity.display_name == "Mathis"
    assert login.identity.profile_image_url == "https://example.invalid/me.png"


def test_connect_stores_the_authorized_tokens() -> None:
    connections = _ConnectionService()
    user_id = UUID(int=1)

    async def _login_and_connect() -> None:
        login = await _provider(connections).authorize(authorization_code="c")
        await login.connect(user_id=user_id)

    asyncio.run(_login_and_connect())

    assert connections.upserted == (user_id, _TOKENS, _PROFILE)
