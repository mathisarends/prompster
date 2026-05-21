from dishka import Provider, Scope, provide

from backend.features.oauth_connections.domain import OAuthConnectionRepository
from backend.features.user.application import UserService
from backend.features.user.domain import UserRepository


class UserProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def provide_user_service(
        self,
        user_repository: UserRepository,
        oauth_connection_repository: OAuthConnectionRepository,
    ) -> UserService:
        return UserService(
            user_repository=user_repository,
            oauth_connection_repository=oauth_connection_repository,
        )
