from backend.features.auth.application.exceptions import InvalidCredentialsException
from backend.features.auth.application.ports import PasswordHasher, TokenIssuer
from backend.features.auth.application.schemas import AuthSession
from backend.features.auth.domain import AuthUserRepository


class LoginUserHandler:
    def __init__(
        self,
        user_repository: AuthUserRepository,
        password_hasher: PasswordHasher,
        token_issuer: TokenIssuer,
    ) -> None:
        self._user_repository = user_repository
        self._password_hasher = password_hasher
        self._token_issuer = token_issuer

    async def handle(self, *, email: str, password: str) -> AuthSession:
        normalized_email = email.strip().lower()
        user = await self._user_repository.get_by_email(email=normalized_email)

        if user is None:
            raise InvalidCredentialsException("Invalid email or password")

        if not self._password_hasher.verify(password, user.password_hash):
            raise InvalidCredentialsException("Invalid email or password")

        return self._token_issuer.create_session(user_id=user.id)
