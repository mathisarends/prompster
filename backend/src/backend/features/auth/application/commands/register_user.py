from backend.features.auth.application.exceptions import UserAlreadyExistsException
from backend.features.auth.application.ports import PasswordHasher, TokenIssuer
from backend.features.auth.application.schemas import AuthSession
from backend.features.auth.domain import AuthUser, AuthUserRepository


class RegisterUserHandler:
    def __init__(
        self,
        user_repository: AuthUserRepository,
        password_hasher: PasswordHasher,
        token_issuer: TokenIssuer,
    ) -> None:
        self._user_repository = user_repository
        self._password_hasher = password_hasher
        self._token_issuer = token_issuer

    async def handle(self, *, name: str, email: str, password: str) -> AuthSession:
        normalized_email = email.strip().lower()
        existing_user = await self._user_repository.get_by_email(email=normalized_email)
        if existing_user is not None:
            raise UserAlreadyExistsException("User already exists")

        user = AuthUser(
            name=name.strip(),
            email=normalized_email,
            password_hash=self._password_hasher.hash(password),
        )
        created_user = await self._user_repository.create(user=user)

        return self._token_issuer.create_session(user_id=created_user.id)
