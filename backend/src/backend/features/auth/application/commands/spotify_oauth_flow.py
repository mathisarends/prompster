from __future__ import annotations

import secrets
from typing import TYPE_CHECKING

from backend.features.auth.application.ports import TokenIssuer
from backend.features.auth.application.schemas import (
    AuthSession,
    SpotifyLoginAuthorizationRequest,
    SpotifyLoginCallbackResult,
)
from backend.features.user.domain import (
    AuthIdentity,
    AuthProvider,
    User,
    UserRepository,
)

if TYPE_CHECKING:
    from backend.features.oauth_connections.application.ports import (
        SpotifyOAuthProvider,
    )
    from backend.features.oauth_connections.application.spotify_oauth_connection_service import (
        SpotifyOAuthConnectionService,
    )


class SpotifyOAuthFlow:
    _STATE_TOKEN_BYTES = 32

    def __init__(
        self,
        user_repository: UserRepository,
        spotify_oauth_client: SpotifyOAuthProvider,
        token_issuer: TokenIssuer,
        connection_service: SpotifyOAuthConnectionService,
    ) -> None:
        self._user_repository = user_repository
        self._spotify_oauth_client = spotify_oauth_client
        self._token_issuer = token_issuer
        self._connection_service = connection_service

    def login(self) -> SpotifyLoginAuthorizationRequest:
        oauth_state = secrets.token_urlsafe(self._STATE_TOKEN_BYTES)
        authorization_url = self._spotify_oauth_client.build_authorization_url(
            state=oauth_state,
        )
        return SpotifyLoginAuthorizationRequest(
            authorization_url=authorization_url,
            state=oauth_state,
        )

    async def callback(
        self,
        *,
        code: str | None,
        state: str,
        error: str | None,
        expected_oauth_state: str | None,
    ) -> SpotifyLoginCallbackResult:
        if error is not None:
            return SpotifyLoginCallbackResult.error(reason=error)

        if code is None:
            return SpotifyLoginCallbackResult.error(reason="missing_code")

        if expected_oauth_state is None or not secrets.compare_digest(
            expected_oauth_state,
            state,
        ):
            return SpotifyLoginCallbackResult.error(reason="invalid_credentials")

        try:
            tokens = await self._spotify_oauth_client.exchange_code_for_tokens(
                authorization_code=code,
            )
            profile = await self._spotify_oauth_client.fetch_spotify_user_profile(
                access_token=tokens.access_token,
            )
        except ValueError:
            return SpotifyLoginCallbackResult.error(reason="invalid_credentials")

        if profile.email is None:
            return SpotifyLoginCallbackResult.error(reason="email_missing")

        normalized_email = profile.email.strip().lower()

        existing_user = await self._user_repository.get_by_auth_identity(
            provider=AuthProvider.SPOTIFY,
            subject=profile.spotify_user_id,
        )

        if existing_user is None:
            email_user = await self._user_repository.get_by_email(
                email=normalized_email
            )
            if email_user is not None:
                return SpotifyLoginCallbackResult.error(reason="email_taken")

            raw_name = (profile.display_name or "").strip()
            fallback_name = normalized_email.split("@", maxsplit=1)[0]
            display_name = raw_name or fallback_name
            user = User(
                name=display_name,
                email=normalized_email,
                profile_image_url=profile.profile_image_url,
            )
            existing_user = await self._user_repository.create_with_auth_identity(
                user=user,
                auth_identity=AuthIdentity(
                    user_id=user.id,
                    provider=AuthProvider.SPOTIFY,
                    subject=profile.spotify_user_id,
                ),
            )
        else:
            existing_user = await self._sync_profile_image(
                user=existing_user,
                profile_image_url=profile.profile_image_url,
            )

        try:
            await self._connection_service.upsert_from_tokens(
                user_id=existing_user.id,
                tokens=tokens,
                profile=profile,
            )
        except ValueError:
            return SpotifyLoginCallbackResult.error(reason="no_refresh_token")

        session = self._token_issuer.create_session(user_id=existing_user.id)
        return SpotifyLoginCallbackResult.success(session=session)

    async def _sync_profile_image(
        self,
        *,
        user: User,
        profile_image_url: str | None,
    ) -> User:
        if profile_image_url is None or user.profile_image_url == profile_image_url:
            return user

        user.profile_image_url = profile_image_url
        return await self._user_repository.update(user=user)
