from backend.features.user.infrastructure.repository import SqlUserRepository
from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from backend.env import EnvSettings, FeatureToggleSettings
from backend.features.auth.application import (
    GoogleOAuthFlow,
    SessionRefresher,
    SpotifyOAuthFlow,
)
from backend.features.auth.application.ports import GoogleOAuthProvider, TokenIssuer
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
from backend.features.oauth_connections.application.spotify_oauth_connection_service import (
    SpotifyOAuthConnectionService,
)
from backend.features.oauth_connections.infrastructure.spotify_auth_settings import (
    SpotifyAuthSettings,
)
from backend.features.oauth_connections.application import (
    SpotifyOAuthProvider,
)
from backend.features.user.domain import UserRepository
from backend.shared.email import EmailSender


class AuthProvider(Provider):
    @provide(scope=Scope.APP)
    def provide_env_settings(self) -> EnvSettings:
        return EnvSettings()

    @provide(scope=Scope.APP)
    def provide_feature_toggle_settings(self) -> FeatureToggleSettings:
        return FeatureToggleSettings()

    @provide(scope=Scope.APP)
    def provide_auth_settings(self) -> AuthSettings:
        return AuthSettings()

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
        email_sender: EmailSender,
        feature_toggle_settings: FeatureToggleSettings,
    ) -> GoogleOAuthFlow:
        return GoogleOAuthFlow(
            user_repository=user_repository,
            google_oauth_provider=google_oauth_provider,
            token_issuer=token_issuer,
            email_sender=email_sender,
            send_welcome_email_on_auth_signup=feature_toggle_settings.send_welcome_email_on_auth_signup,
        )

    @provide(scope=Scope.REQUEST)
    def provide_spotify_oauth_flow(
        self,
        user_repository: UserRepository,
        spotify_oauth_provider: SpotifyOAuthProvider,
        token_issuer: TokenIssuer,
        connection_service: SpotifyOAuthConnectionService,
        email_sender: EmailSender,
        feature_toggle_settings: FeatureToggleSettings,
    ) -> SpotifyOAuthFlow:
        return SpotifyOAuthFlow(
            user_repository=user_repository,
            spotify_oauth_client=spotify_oauth_provider,
            token_issuer=token_issuer,
            connection_service=connection_service,
            email_sender=email_sender,
            send_welcome_email_on_auth_signup=feature_toggle_settings.send_welcome_email_on_auth_signup,
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
            signing_secret=auth_settings.jwt_secret,
            frontend_base_url=auth_settings.frontend_base_url,
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
        auth_settings: AuthSettings,
        env_config: EnvSettings,
    ) -> AuthCookies:
        return AuthCookies(auth_settings=auth_settings, env_config=env_config)

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
            signing_secret=auth_settings.jwt_secret,
            frontend_base_url=auth_settings.frontend_base_url,
            env_config=env_config,
        )
