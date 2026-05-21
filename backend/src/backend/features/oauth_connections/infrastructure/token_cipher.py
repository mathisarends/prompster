from cryptography.fernet import Fernet, InvalidToken

from backend.features.oauth_connections.application.ports import OAuthTokenCipher


class FernetOAuthTokenCipher(OAuthTokenCipher):
    def __init__(self, encryption_key: str) -> None:
        normalized_key = encryption_key.strip()
        if not normalized_key:
            raise ValueError("OAuth token encryption key is not configured")
        self._fernet = Fernet(normalized_key.encode("utf-8"))

    def encrypt(self, plaintext: str) -> bytes:
        normalized_plaintext = plaintext.strip()
        if not normalized_plaintext:
            raise ValueError("OAuth refresh token must not be empty")
        return self._fernet.encrypt(normalized_plaintext.encode("utf-8"))

    def decrypt(self, ciphertext: bytes) -> str:
        try:
            return self._fernet.decrypt(ciphertext).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("OAuth refresh token could not be decrypted") from exc
