from argon2 import PasswordHasher as Argon2Hasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from backend.features.auth.application.ports import PasswordHasher


class Argon2PasswordHasher(PasswordHasher):
    def __init__(self) -> None:
        self._hasher = Argon2Hasher(
            time_cost=3,
            memory_cost=65536,
            parallelism=2,
        )

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password: str, hashed: str) -> bool:
        try:
            return self._hasher.verify(hashed, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False
