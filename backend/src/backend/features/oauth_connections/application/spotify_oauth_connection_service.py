import secrets
from datetime import datetime, timezone
from uuid import UUID

from backend.features.oauth_connections.application.ports import (
    OAuthTokenCipher,
    SpotifyOAuthProvider,
)
from backend.features.oauth_connections.application.schemas import (
    SpotifyAuthorizationRequest,
    SpotifyCallbackResult,
    SpotifyTokens,
    SpotifyUserProfile,
)
from backend.features.oauth_connections.domain import (
    OAuthConnection,
    OAuthConnectionRepository,
    OAuthProvider,
)


class SpotifyOAuthConnectionService:
    _STATE_TOKEN_BYTES = 32

    def __init__(
        self,
        connection_repository: OAuthConnectionRepository,
        spotify_oauth_provider: SpotifyOAuthProvider,
        token_cipher: OAuthTokenCipher,
    ) -> None:
        self._connection_repository = connection_repository
        self._spotify_oauth_provider = spotify_oauth_provider
        self._token_cipher = token_cipher

    def start_connect(self, *, user_id: UUID) -> SpotifyAuthorizationRequest:
        state_payload = f"{user_id}:{secrets.token_urlsafe(self._STATE_TOKEN_BYTES)}"
        authorization_url = self._spotify_oauth_provider.build_authorization_url(
            state=state_payload,
        )
        return SpotifyAuthorizationRequest(
            authorization_url=authorization_url,
            state=state_payload,
        )

    async def complete_connect(
        self,
        *,
        authenticated_user_id: UUID,
        code: str | None,
        state: str,
        error: str | None,
        expected_oauth_state: str | None,
    ) -> SpotifyCallbackResult:
        if error is not None:
            return SpotifyCallbackResult.error(reason=error)

        if code is None:
            return SpotifyCallbackResult.error(reason="missing_code")

        if expected_oauth_state is None or not secrets.compare_digest(
            expected_oauth_state,
            state,
        ):
            return SpotifyCallbackResult.error(reason="invalid_state")

        state_user_id_str, separator, _state_nonce = state.partition(":")
        if separator != ":":
            return SpotifyCallbackResult.error(reason="invalid_state")

        if state_user_id_str != str(authenticated_user_id):
            return SpotifyCallbackResult.error(reason="user_mismatch")

        try:
            tokens = await self._spotify_oauth_provider.exchange_code_for_tokens(
                authorization_code=code,
            )
            if tokens.refresh_token is None:
                return SpotifyCallbackResult.error(reason="no_refresh_token")
            profile = await self._spotify_oauth_provider.fetch_spotify_user_profile(
                access_token=tokens.access_token,
            )
        except ValueError:
            return SpotifyCallbackResult.error(reason="spotify_exchange_failed")

        existing = await self._connection_repository.get(
            user_id=authenticated_user_id,
            provider=OAuthProvider.SPOTIFY,
        )
        connection = OAuthConnection(
            user_id=authenticated_user_id,
            provider=OAuthProvider.SPOTIFY,
            provider_user_id=profile.spotify_user_id,
            encrypted_refresh_token=self._token_cipher.encrypt(tokens.refresh_token),
            scope=tokens.scope,
            connected_at=datetime.now(timezone.utc),
            is_premium=profile.is_premium,
            id=existing.id if existing is not None else None,
            created_time=existing.created_at if existing is not None else None,
        )
        await self._connection_repository.save(connection=connection)
        return SpotifyCallbackResult.success()

    async def upsert_from_tokens(
        self,
        *,
        user_id: UUID,
        tokens: SpotifyTokens,
        profile: SpotifyUserProfile,
    ) -> None:
        existing = await self._connection_repository.get(
            user_id=user_id,
            provider=OAuthProvider.SPOTIFY,
        )

        if tokens.refresh_token is not None:
            encrypted_refresh = self._token_cipher.encrypt(tokens.refresh_token)
        elif existing is not None:
            encrypted_refresh = existing.encrypted_refresh_token
        else:
            raise ValueError("no_refresh_token")

        connection = OAuthConnection(
            user_id=user_id,
            provider=OAuthProvider.SPOTIFY,
            provider_user_id=profile.spotify_user_id,
            encrypted_refresh_token=encrypted_refresh,
            scope=tokens.scope,
            connected_at=datetime.now(timezone.utc),
            is_premium=profile.is_premium,
            id=existing.id if existing is not None else None,
            created_time=existing.created_at if existing is not None else None,
        )
        await self._connection_repository.save(connection=connection)

    async def refresh_premium_status(self, *, user_id: UUID) -> bool | None:
        connection = await self._connection_repository.get(
            user_id=user_id,
            provider=OAuthProvider.SPOTIFY,
        )
        if connection is None:
            return None

        try:
            refresh_token = self._token_cipher.decrypt(
                connection.encrypted_refresh_token
            )
            tokens = await self._spotify_oauth_provider.refresh_access_token(
                refresh_token=refresh_token,
            )
            profile = await self._spotify_oauth_provider.fetch_spotify_user_profile(
                access_token=tokens.access_token,
            )
        except ValueError:
            return None

        connection.update_premium_status(is_premium=profile.is_premium)
        await self._connection_repository.save(connection=connection)
        return profile.is_premium

    async def disconnect(self, *, user_id: UUID) -> None:
        await self._connection_repository.delete(
            user_id=user_id,
            provider=OAuthProvider.SPOTIFY,
        )
