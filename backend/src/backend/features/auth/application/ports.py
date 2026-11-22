from abc import ABC, abstractmethod
from uuid import UUID

from backend.features.auth.domain import GoogleIdentity, SpotifyIdentity


class GoogleOAuthProvider(ABC):
    @abstractmethod
    def build_authorization_url(self, *, state: str) -> str: ...

    @abstractmethod
    async def exchange_code_for_identity(
        self,
        *,
        authorization_code: str,
    ) -> GoogleIdentity: ...


class SpotifyLogin(ABC):
    """A Spotify authorization that is not bound to a user yet."""

    @property
    @abstractmethod
    def identity(self) -> SpotifyIdentity: ...

    @abstractmethod
    async def connect(self, *, user_id: UUID) -> None:
        """Store the Spotify connection; raises ValueError without a refresh token."""


class SpotifyLoginProvider(ABC):
    @abstractmethod
    def build_authorization_url(self, *, state: str) -> str: ...

    @abstractmethod
    async def authorize(self, *, authorization_code: str) -> SpotifyLogin:
        """Raises ValueError when Spotify rejects the authorization code."""
