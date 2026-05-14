from dishka import Provider, Scope, provide

from backend.env import EnvSettings
from backend.features.auth.application import (
    LoginUserHandler,
    RefreshSessionHandler,
    RegisterUserHandler,
)
from backend.features.auth.application.ports import PasswordHasher, TokenIssuer
from backend.features.auth.domain import AuthUserRepository
from backend.features.auth.infrastructure.auth_settings import AuthSettings
from backend.features.auth.infrastructure.jwt_token_issuer import JwtTokenIssuer
from backend.features.auth.infrastructure.orm import InMemoryAuthUserRepository
from backend.features.auth.infrastructure.hasher import Argon2PasswordHasher
from backend.features.auth.presentation.cookies import AuthCookies


class AuthProvider(Provider):
    @provide(scope=Scope.APP)
    def provide_env_settings(self) -> EnvSettings:
        return EnvSettings()

    @provide(scope=Scope.APP)
    def provide_auth_settings(self) -> AuthSettings:
        return AuthSettings()

    @provide(scope=Scope.APP)
    def provide_password_hasher(self) -> PasswordHasher:
        return Argon2PasswordHasher()

    @provide(scope=Scope.APP)
    def provide_token_issuer(
        self,
        auth_settings: AuthSettings,
    ) -> TokenIssuer:
        return JwtTokenIssuer(auth_settings=auth_settings)

    @provide(scope=Scope.APP)
    def provide_user_repository(self) -> AuthUserRepository:
        return InMemoryAuthUserRepository()

    @provide(scope=Scope.REQUEST)
    def provide_register_user_handler(
        self,
        user_repository: AuthUserRepository,
        password_hasher: PasswordHasher,
        token_issuer: TokenIssuer,
    ) -> RegisterUserHandler:
        return RegisterUserHandler(
            user_repository=user_repository,
            password_hasher=password_hasher,
            token_issuer=token_issuer,
        )

    @provide(scope=Scope.REQUEST)
    def provide_login_user_handler(
        self,
        user_repository: AuthUserRepository,
        password_hasher: PasswordHasher,
        token_issuer: TokenIssuer,
    ) -> LoginUserHandler:
        return LoginUserHandler(
            user_repository=user_repository,
            password_hasher=password_hasher,
            token_issuer=token_issuer,
        )

    @provide(scope=Scope.REQUEST)
    def provide_refresh_session_handler(
        self,
        user_repository: AuthUserRepository,
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
