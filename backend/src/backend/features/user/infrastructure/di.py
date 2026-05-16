from dishka import Provider, Scope, provide

from backend.features.user.application import GetMeHandler
from backend.features.user.domain import UserRepository


class UserProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def provide_get_me_handler(
        self,
        user_repository: UserRepository,
    ) -> GetMeHandler:
        return GetMeHandler(user_repository=user_repository)
