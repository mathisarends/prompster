from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from backend.env import EnvSettings
from backend.features.auth.application import (
    GoogleCallbackHandler,
    GoogleLoginHandler,
    RefreshSessionHandler,
)
from backend.features.auth.application.ports import GoogleOAuthProvider, TokenIssuer
from backend.features.auth.infrastructure.auth_settings import (
    AuthSettings,
    GoogleAuthSettings,
)
from backend.features.auth.infrastructure.google_oauth_client import GoogleOAuthClient
from backend.features.auth.infrastructure.jwt_token_issuer import JwtTokenIssuer
from backend.features.auth.infrastructure.orm import SqlUserRepository
from backend.features.user.domain import UserRepository
from backend.features.auth.presentation.cookies import AuthCookies


class AuthProvider(Provider):
    @provide(scope=Scope.APP)
    def provide_env_settings(self) -> EnvSettings:
        return EnvSettings()

    @provide(scope=Scope.APP)
    def provide_auth_settings(self) -> AuthSettings:
        return AuthSettings()

    @provide(scope=Scope.APP)
    def provide_google_auth_settings(self) -> GoogleAuthSettings:
        return GoogleAuthSettings()

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
    def provide_google_callback_handler(
        self,
        user_repository: UserRepository,
        google_oauth_provider: GoogleOAuthProvider,
        token_issuer: TokenIssuer,
    ) -> GoogleCallbackHandler:
        return GoogleCallbackHandler(
            user_repository=user_repository,
            google_oauth_provider=google_oauth_provider,
            token_issuer=token_issuer,
        )

    @provide(scope=Scope.REQUEST)
    def provide_google_login_handler(
        self,
        google_oauth_provider: GoogleOAuthProvider,
    ) -> GoogleLoginHandler:
        return GoogleLoginHandler(google_oauth_provider=google_oauth_provider)

    @provide(scope=Scope.REQUEST)
    def provide_refresh_session_handler(
        self,
        user_repository: UserRepository,
        token_issuer: TokenIssuer,
    ) -> RefreshSessionHandler:
        return RefreshSessionHandler(
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
