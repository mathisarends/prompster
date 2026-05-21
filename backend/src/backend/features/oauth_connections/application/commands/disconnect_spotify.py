from uuid import UUID

from backend.features.oauth_connections.domain import (
    OAuthConnectionRepository,
    OAuthProvider,
)


class DisconnectSpotifyHandler:
    def __init__(self, connection_repository: OAuthConnectionRepository) -> None:
        self._connection_repository = connection_repository

    async def handle(self, *, user_id: UUID) -> None:
        await self._connection_repository.delete(
            user_id=user_id,
            provider=OAuthProvider.SPOTIFY,
        )
