import secrets
from uuid import UUID

from backend.features.auth.application.ports import PasswordHasher, TokenGenerator

from argon2 import PasswordHasher as Argon2Hasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError


class Argon2PasswordHasher(PasswordHasher):
    def __init__(self) -> None:
        self._hasher = Argon2Hasher(
            time_cost=3,
            memory_cost=65536,
            parallelism=2,
        )

    def hash_password(self, *, plain_password: str) -> str:
        return self._hasher.hash(plain_password)

    def verify_password(self, *, plain_password: str, password_hash: str) -> bool:
        try:
            return self._hasher.verify(password_hash, plain_password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False


class RandomTokenGenerator(TokenGenerator):
    def create_access_token(self, *, user_id: UUID) -> str:
        return f"{user_id}:{secrets.token_urlsafe(24)}"

    def create_refresh_token(self) -> str:
        return secrets.token_urlsafe(48)
