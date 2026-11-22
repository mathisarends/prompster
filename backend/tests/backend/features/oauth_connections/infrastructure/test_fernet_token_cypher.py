import pytest
from cryptography.fernet import Fernet

from backend.features.oauth_connections.infrastructure.fernet_token_cypher import (
    FernetOAuthTokenCipher,
)


class TestFernetOAuthTokenCipher:
    def test_encrypts_and_decrypts_normalized_refresh_token(self) -> None:
        cipher = FernetOAuthTokenCipher(f"  {Fernet.generate_key().decode()}  ")

        encrypted_token = cipher.encrypt("  refresh-token  ")

        assert encrypted_token != b"refresh-token"
        assert cipher.decrypt(encrypted_token) == "refresh-token"

    @pytest.mark.parametrize("encryption_key", ["", "   "])
    def test_requires_configured_encryption_key(self, encryption_key: str) -> None:
        with pytest.raises(ValueError, match="not configured"):
            FernetOAuthTokenCipher(encryption_key)

    @pytest.mark.parametrize("plaintext", ["", "   "])
    def test_rejects_empty_refresh_token(self, plaintext: str) -> None:
        cipher = FernetOAuthTokenCipher(Fernet.generate_key().decode())

        with pytest.raises(ValueError, match="must not be empty"):
            cipher.encrypt(plaintext)

    def test_rejects_ciphertext_not_created_with_its_key(self) -> None:
        cipher = FernetOAuthTokenCipher(Fernet.generate_key().decode())
        foreign_ciphertext = Fernet(Fernet.generate_key()).encrypt(b"refresh-token")

        with pytest.raises(ValueError, match="could not be decrypted"):
            cipher.decrypt(foreign_ciphertext)
