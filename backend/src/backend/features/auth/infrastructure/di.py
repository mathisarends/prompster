from typing import Final

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from backend.env import EnvSettings
from backend.features.auth.application import (
    GoogleOAuthFlow,
    SessionRefresher,
    SpotifyOAuthFlow,
)
from backend.features.auth.application.ports import (
    GoogleOAuthProvider,
    SpotifyLoginProvider,
)
from backend.features.auth.infrastructure.auth_settings import AuthSettings
from backend.features.auth.infrastructure.google_auth_settings import GoogleAuthSettings
from backend.features.auth.infrastructure.google_oauth_client import GoogleOAuthClient
from backend.features.auth.infrastructure.jwt_token_issuer import JwtTokenIssuer
from backend.features.auth.infrastructure.oauth_state_settings import OAuthStateSettings
from backend.features.auth.presentation.cookies import AuthCookies
from backend.features.auth.presentation.oauth_state_cookies import (
    GoogleOAuthStateCookies,
    SpotifyLoginOAuthStateCookies,
)
from backend.features.oauth_connections.infrastructure.spotify_auth_settings import (
    SpotifyAuthSettings,
)
from backend.features.user.domain import UserRepository
from backend.features.user.infrastructure.repository import SqlUserRepository
from backend.presentation.authentication import AuthCookieSettings
from backend.shared.authentication import TokenIssuer

_SECONDS_PER_MINUTE: Final = 60
_SECONDS_PER_DAY: Final = 60 * 60 * 24


class AuthProvider(Provider):
    @provide(scope=Scope.APP)
    def provide_env_settings(self) -> EnvSettings:
        return EnvSettings()

    @provide(scope=Scope.APP)
    def provide_auth_settings(self) -> AuthSettings:
        return AuthSettings()

    @provide(scope=Scope.APP)
    def provide_auth_cookie_settings(
        self,
        auth_settings: AuthSettings,
    ) -> AuthCookieSettings:
        return AuthCookieSettings(
            access_token_name=auth_settings.access_token_cookie_name,
            refresh_token_name=auth_settings.jwt_refresh_token_cookie_name,
            access_token_max_age_seconds=(
                auth_settings.jwt_access_token_expire_minutes * _SECONDS_PER_MINUTE
            ),
            refresh_token_max_age_seconds=(
                auth_settings.jwt_refresh_token_expire_days * _SECONDS_PER_DAY
            ),
            same_site_dev=auth_settings.cookie_samesite_dev.value,
            same_site_prod=auth_settings.cookie_samesite_prod.value,
        )

    @provide(scope=Scope.APP)
    def provide_google_auth_settings(self) -> GoogleAuthSettings:
        return GoogleAuthSettings()

    @provide(scope=Scope.APP)
    def provide_oauth_state_settings(self) -> OAuthStateSettings:
        return OAuthStateSettings()

    @provide(scope=Scope.APP)
    def provide_token_issuer(
        self,
        auth_settings: AuthSettings,
    ) -> TokenIssuer:
        return JwtTokenIssuer(auth_settings=auth_settings)

    @provide(scope=Scope.APP)
    def provide_google_oauth_provider(
        self,
        google_auth_settings: GoogleAuthSettings,
    ) -> GoogleOAuthProvider:
        return GoogleOAuthClient(google_auth_settings=google_auth_settings)

    @provide(scope=Scope.REQUEST)
    def provide_user_repository(self, session: AsyncSession) -> UserRepository:
        return SqlUserRepository(session=session)

    @provide(scope=Scope.REQUEST)
    def provide_google_oauth_flow(
        self,
        user_repository: UserRepository,
        google_oauth_provider: GoogleOAuthProvider,
        token_issuer: TokenIssuer,
    ) -> GoogleOAuthFlow:
        return GoogleOAuthFlow(
            user_repository=user_repository,
            google_oauth_provider=google_oauth_provider,
            token_issuer=token_issuer,
        )

    @provide(scope=Scope.REQUEST)
    def provide_spotify_oauth_flow(
        self,
        user_repository: UserRepository,
        spotify_login_provider: SpotifyLoginProvider,
        token_issuer: TokenIssuer,
    ) -> SpotifyOAuthFlow:
        return SpotifyOAuthFlow(
            user_repository=user_repository,
            spotify_login_provider=spotify_login_provider,
            token_issuer=token_issuer,
        )

    @provide(scope=Scope.REQUEST)
    def provide_spotify_login_state_cookies(
        self,
        auth_settings: AuthSettings,
        spotify_auth_settings: SpotifyAuthSettings,
        oauth_state_settings: OAuthStateSettings,
        env_config: EnvSettings,
    ) -> SpotifyLoginOAuthStateCookies:
        return SpotifyLoginOAuthStateCookies(
            cookie_name=spotify_auth_settings.login_state_cookie_name,
            ttl_seconds=oauth_state_settings.ttl_seconds,
            signing_secret=auth_settings.jwt_secret.get_secret_value(),
            frontend_base_url=env_config.frontend_base_url,
            env_config=env_config,
        )

    @provide(scope=Scope.REQUEST)
    def provide_session_refresher(
        self,
        user_repository: UserRepository,
        token_issuer: TokenIssuer,
    ) -> SessionRefresher:
        return SessionRefresher(
            user_repository=user_repository,
            token_issuer=token_issuer,
        )

    @provide(scope=Scope.REQUEST)
    def provide_auth_cookies(
        self,
        cookie_settings: AuthCookieSettings,
        env_config: EnvSettings,
    ) -> AuthCookies:
        return AuthCookies(cookie_settings=cookie_settings, env_config=env_config)

    @provide(scope=Scope.REQUEST)
    def provide_google_oauth_state_cookies(
        self,
        auth_settings: AuthSettings,
        google_auth_settings: GoogleAuthSettings,
        oauth_state_settings: OAuthStateSettings,
        env_config: EnvSettings,
    ) -> GoogleOAuthStateCookies:
        return GoogleOAuthStateCookies(
            cookie_name=google_auth_settings.state_cookie_name,
            ttl_seconds=oauth_state_settings.ttl_seconds,
            signing_secret=auth_settings.jwt_secret.get_secret_value(),
            frontend_base_url=env_config.frontend_base_url,
            env_config=env_config,
        )
