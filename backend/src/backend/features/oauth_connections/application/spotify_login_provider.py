from uuid import UUID

from backend.features.auth.application.ports import SpotifyLogin, SpotifyLoginProvider
from backend.features.auth.application.schemas import SpotifyIdentity
from backend.features.oauth_connections.application.ports import SpotifyOAuthProvider
from backend.features.oauth_connections.application.schemas import (
    SpotifyTokens,
    SpotifyUserProfile,
)
from backend.features.oauth_connections.application.spotify_oauth_connection_service import (
    SpotifyOAuthConnectionService,
)


class SpotifyAccountLoginProvider(SpotifyLoginProvider):
    """Signs users in with Spotify and keeps the account connected afterwards."""

    def __init__(
        self,
        spotify_oauth_provider: SpotifyOAuthProvider,
        connection_service: SpotifyOAuthConnectionService,
    ) -> None:
        self._spotify_oauth_provider = spotify_oauth_provider
        self._connection_service = connection_service

    def build_authorization_url(self, *, state: str) -> str:
        return self._spotify_oauth_provider.build_authorization_url(state=state)

    async def authorize(self, *, authorization_code: str) -> SpotifyLogin:
        tokens = await self._spotify_oauth_provider.exchange_code_for_tokens(
            authorization_code=authorization_code,
        )
        profile = await self._spotify_oauth_provider.fetch_spotify_user_profile(
            access_token=tokens.access_token,
        )
        return _SpotifyAccountLogin(
            tokens=tokens,
            profile=profile,
            connection_service=self._connection_service,
        )


class _SpotifyAccountLogin(SpotifyLogin):
    def __init__(
        self,
        *,
        tokens: SpotifyTokens,
        profile: SpotifyUserProfile,
        connection_service: SpotifyOAuthConnectionService,
    ) -> None:
        self._tokens = tokens
        self._profile = profile
        self._connection_service = connection_service

    @property
    def identity(self) -> SpotifyIdentity:
        return SpotifyIdentity(
            subject=self._profile.spotify_user_id,
            display_name=self._profile.display_name,
            profile_image_url=self._profile.profile_image_url,
        )

    async def connect(self, *, user_id: UUID) -> None:
        await self._connection_service.upsert_from_tokens(
            user_id=user_id,
            tokens=self._tokens,
            profile=self._profile,
        )
