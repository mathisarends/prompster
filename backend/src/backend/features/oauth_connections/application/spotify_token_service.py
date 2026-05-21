from uuid import UUID

from backend.features.oauth_connections.application.exceptions import (
    SpotifyConnectionNotFoundException,
    SpotifyTokenRevokedException,
)
from backend.features.oauth_connections.application.ports import (
    OAuthTokenCipher,
    SpotifyOAuthProvider,
)
from backend.features.oauth_connections.application.schemas import SpotifyAccessToken
from backend.features.oauth_connections.domain import (
    OAuthConnectionRepository,
    OAuthProvider,
)


class SpotifyTokenService:
    def __init__(
        self,
        connection_repository: OAuthConnectionRepository,
        spotify_oauth_provider: SpotifyOAuthProvider,
        token_cipher: OAuthTokenCipher,
    ) -> None:
        self._connection_repository = connection_repository
        self._spotify_oauth_provider = spotify_oauth_provider
        self._token_cipher = token_cipher

    async def get_valid_access_token(self, *, user_id: UUID) -> SpotifyAccessToken:
        connection = await self._connection_repository.get(
            user_id=user_id,
            provider=OAuthProvider.SPOTIFY,
        )
        if connection is None:
            raise SpotifyConnectionNotFoundException()

        try:
            refresh_token = self._token_cipher.decrypt(
                connection.encrypted_refresh_token
            )
            tokens = await self._spotify_oauth_provider.refresh_access_token(
                refresh_token=refresh_token,
            )
        except ValueError as exc:
            await self._connection_repository.delete(
                user_id=user_id,
                provider=OAuthProvider.SPOTIFY,
            )
            raise SpotifyTokenRevokedException() from exc

        if tokens.refresh_token is not None and tokens.refresh_token != refresh_token:
            connection.rotate_refresh_token(
                new_encrypted_refresh_token=self._token_cipher.encrypt(
                    tokens.refresh_token,
                )
            )
            await self._connection_repository.save(connection=connection)

        return SpotifyAccessToken(
            access_token=tokens.access_token,
            expires_in=tokens.expires_in,
            scope=tokens.scope,
        )
