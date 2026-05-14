from dishka import Provider, Scope, provide

from backend.env import EnvSettings
from backend.features.auth.application import (
    LoginUserHandler,
    RefreshSessionHandler,
    RegisterUserHandler,
)
from backend.features.auth.application.ports import PasswordHasher, TokenGenerator
from backend.features.auth.domain import AuthUserRepository, RefreshSessionRepository
from backend.features.auth.infrastructure.auth_settings import AuthSettings
from backend.features.auth.infrastructure.orm import (
    InMemoryAuthUserRepository,
    InMemoryRefreshSessionRepository,
)
from backend.features.auth.infrastructure.security import (
    Argon2PasswordHasher,
    RandomTokenGenerator,
)
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
    def provide_token_generator(self) -> TokenGenerator:
        return RandomTokenGenerator()

    @provide(scope=Scope.APP)
    def provide_user_repository(self) -> AuthUserRepository:
        return InMemoryAuthUserRepository()

    @provide(scope=Scope.APP)
    def provide_refresh_session_repository(self) -> RefreshSessionRepository:
        return InMemoryRefreshSessionRepository()

    @provide(scope=Scope.REQUEST)
    def provide_register_user_handler(
        self,
        user_repository: AuthUserRepository,
        refresh_session_repository: RefreshSessionRepository,
        password_hasher: PasswordHasher,
        token_generator: TokenGenerator,
        auth_settings: AuthSettings,
    ) -> RegisterUserHandler:
        return RegisterUserHandler(
            user_repository=user_repository,
            refresh_session_repository=refresh_session_repository,
            password_hasher=password_hasher,
            token_generator=token_generator,
            refresh_token_expire_days=auth_settings.jwt_refresh_token_expire_days,
        )

    @provide(scope=Scope.REQUEST)
    def provide_login_user_handler(
        self,
        user_repository: AuthUserRepository,
        refresh_session_repository: RefreshSessionRepository,
        password_hasher: PasswordHasher,
        token_generator: TokenGenerator,
        auth_settings: AuthSettings,
    ) -> LoginUserHandler:
        return LoginUserHandler(
            user_repository=user_repository,
            refresh_session_repository=refresh_session_repository,
            password_hasher=password_hasher,
            token_generator=token_generator,
            refresh_token_expire_days=auth_settings.jwt_refresh_token_expire_days,
        )

    @provide(scope=Scope.REQUEST)
    def provide_refresh_session_handler(
        self,
        user_repository: AuthUserRepository,
        refresh_session_repository: RefreshSessionRepository,
        token_generator: TokenGenerator,
        auth_settings: AuthSettings,
    ) -> RefreshSessionHandler:
        return RefreshSessionHandler(
            user_repository=user_repository,
            refresh_session_repository=refresh_session_repository,
            token_generator=token_generator,
            refresh_token_expire_days=auth_settings.jwt_refresh_token_expire_days,
        )

    @provide(scope=Scope.REQUEST)
    def provide_auth_cookies(
        self,
        auth_settings: AuthSettings,
        env_config: EnvSettings,
    ) -> AuthCookies:
        return AuthCookies(auth_settings=auth_settings, env_config=env_config)
