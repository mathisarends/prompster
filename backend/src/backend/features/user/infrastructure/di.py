from dishka import Provider, Scope, provide

from backend.features.user.application import UserService
from backend.features.user.domain import UserRepository


class UserProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def provide_user_service(
        self,
        user_repository: UserRepository,
    ) -> UserService:
        return UserService(user_repository=user_repository)
