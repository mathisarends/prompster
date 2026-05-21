from abc import ABC, abstractmethod

from backend.features.oauth_connections.application.schemas import SpotifyTokens


class SpotifyOAuthProvider(ABC):
    @abstractmethod
    def build_authorization_url(self, *, state: str) -> str: ...

    @abstractmethod
    async def exchange_code_for_tokens(
        self,
        *,
        authorization_code: str,
    ) -> SpotifyTokens: ...

    @abstractmethod
    async def fetch_spotify_user_id(self, *, access_token: str) -> str: ...

    @abstractmethod
    async def refresh_access_token(self, *, refresh_token: str) -> SpotifyTokens: ...


class OAuthTokenCipher(ABC):
    @abstractmethod
    def encrypt(self, plaintext: str) -> bytes: ...

    @abstractmethod
    def decrypt(self, ciphertext: bytes) -> str: ...
