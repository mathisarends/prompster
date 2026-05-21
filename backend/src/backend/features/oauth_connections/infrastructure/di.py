from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from backend.env import EnvSettings
from backend.features.auth.infrastructure.auth_settings import AuthSettings
from backend.features.auth.infrastructure.oauth_state_settings import OAuthStateSettings
from backend.features.oauth_connections.application import (
    OAuthTokenCipher,
    SpotifyOAuthConnectionService,
    SpotifyOAuthProvider,
    SpotifyTokenService,
)
from backend.features.oauth_connections.domain import OAuthConnectionRepository
from backend.features.oauth_connections.infrastructure.repository import (
    SqlOAuthConnectionRepository,
)
from backend.features.oauth_connections.infrastructure.spotify_auth_settings import (
    SpotifyAuthSettings,
)
from backend.features.oauth_connections.infrastructure.spotify_oauth_client import (
    SpotifyOAuthClient,
)
from backend.features.oauth_connections.infrastructure.token_cipher import (
    FernetOAuthTokenCipher,
)
from backend.features.oauth_connections.presentation.spotify_oauth_state_cookies import (
    SpotifyOAuthStateCookies,
)


class OAuthConnectionsProvider(Provider):
    @provide(scope=Scope.APP)
    def provide_spotify_auth_settings(self) -> SpotifyAuthSettings:
        return SpotifyAuthSettings()

    @provide(scope=Scope.APP)
    def provide_token_cipher(
        self,
        spotify_auth_settings: SpotifyAuthSettings,
    ) -> OAuthTokenCipher:
        return FernetOAuthTokenCipher(
            encryption_key=spotify_auth_settings.token_encryption_key,
        )

    @provide(scope=Scope.APP)
    def provide_spotify_oauth_provider(
        self,
        spotify_auth_settings: SpotifyAuthSettings,
    ) -> SpotifyOAuthProvider:
        return SpotifyOAuthClient(settings=spotify_auth_settings)

    @provide(scope=Scope.REQUEST)
    def provide_connection_repository(
        self,
        session: AsyncSession,
    ) -> OAuthConnectionRepository:
        return SqlOAuthConnectionRepository(session=session)

    @provide(scope=Scope.REQUEST)
    def provide_oauth_connection_service(
        self,
        repo: OAuthConnectionRepository,
        provider: SpotifyOAuthProvider,
        cipher: OAuthTokenCipher,
    ) -> SpotifyOAuthConnectionService:
        return SpotifyOAuthConnectionService(
            connection_repository=repo,
            spotify_oauth_provider=provider,
            token_cipher=cipher,
        )

    @provide(scope=Scope.REQUEST)
    def provide_token_service(
        self,
        repo: OAuthConnectionRepository,
        provider: SpotifyOAuthProvider,
        cipher: OAuthTokenCipher,
    ) -> SpotifyTokenService:
        return SpotifyTokenService(
            connection_repository=repo,
            spotify_oauth_provider=provider,
            token_cipher=cipher,
        )

    @provide(scope=Scope.REQUEST)
    def provide_spotify_oauth_state_cookies(
        self,
        auth_settings: AuthSettings,
        spotify_auth_settings: SpotifyAuthSettings,
        oauth_state_settings: OAuthStateSettings,
        env_config: EnvSettings,
    ) -> SpotifyOAuthStateCookies:
        return SpotifyOAuthStateCookies(
            cookie_name=spotify_auth_settings.state_cookie_name,
            ttl_seconds=oauth_state_settings.ttl_seconds,
            signing_secret=auth_settings.jwt_secret,
            frontend_base_url=auth_settings.frontend_base_url,
            env_config=env_config,
        )
