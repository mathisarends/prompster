import hashlib
import hmac
import secrets
from uuid import UUID

from backend.features.auth.application.ports import PasswordHasher, TokenGenerator


class PBKDF2PasswordHasher(PasswordHasher):
    _ITERATIONS = 200_000

    def __init__(self, *, pepper: str) -> None:
        self._pepper = pepper.encode("utf-8")

    def hash_password(self, *, plain_password: str) -> str:
        salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8") + self._pepper,
            self._ITERATIONS,
        )
        return f"{salt}${digest.hex()}"

    def verify_password(self, *, plain_password: str, password_hash: str) -> bool:
        try:
            salt, expected_digest = password_hash.split("$", maxsplit=1)
        except ValueError:
            return False

        candidate_digest = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8") + self._pepper,
            self._ITERATIONS,
        ).hex()
        return hmac.compare_digest(candidate_digest, expected_digest)


class RandomTokenGenerator(TokenGenerator):
    def create_access_token(self, *, user_id: UUID) -> str:
        return f"{user_id}:{secrets.token_urlsafe(24)}"

    def create_refresh_token(self) -> str:
        return secrets.token_urlsafe(48)
