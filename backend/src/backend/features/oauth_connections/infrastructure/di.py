from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from backend.features.auth.infrastructure.auth_settings import (
    AuthSettings,
    SpotifyAuthSettings,
)
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
from backend.features.oauth_connections.infrastructure.spotify_oauth_client import (
    SpotifyOAuthClient,
)
from backend.features.oauth_connections.infrastructure.token_cipher import (
    FernetOAuthTokenCipher,
)


class OAuthConnectionsProvider(Provider):
    @provide(scope=Scope.APP)
    def provide_spotify_auth_settings(self) -> SpotifyAuthSettings:
        return SpotifyAuthSettings()

    @provide(scope=Scope.APP)
    def provide_token_cipher(
        self,
        auth_settings: AuthSettings,
    ) -> OAuthTokenCipher:
        return FernetOAuthTokenCipher(
            encryption_key=auth_settings.spotify_token_encryption_key,
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
