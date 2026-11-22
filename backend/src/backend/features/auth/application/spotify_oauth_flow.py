import secrets

from backend.features.auth.application.ports import SpotifyLoginProvider
from backend.shared.authentication import TokenIssuer
from backend.features.auth.application.schemas import (
    SpotifyLoginAuthorizationRequest,
    SpotifyLoginCallbackResult,
)
from backend.features.user.domain import (
    AuthIdentity,
    AuthProvider,
    User,
    UserRepository,
)

_STATE_TOKEN_BYTES = 32


class SpotifyOAuthFlow:
    def __init__(
        self,
        user_repository: UserRepository,
        spotify_login_provider: SpotifyLoginProvider,
        token_issuer: TokenIssuer,
    ) -> None:
        self._user_repository = user_repository
        self._spotify_login_provider = spotify_login_provider
        self._token_issuer = token_issuer

    def login(self) -> SpotifyLoginAuthorizationRequest:
        oauth_state = secrets.token_urlsafe(_STATE_TOKEN_BYTES)
        authorization_url = self._spotify_login_provider.build_authorization_url(
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
            login = await self._spotify_login_provider.authorize(
                authorization_code=code,
            )
        except ValueError:
            return SpotifyLoginCallbackResult.error(reason="invalid_credentials")

        identity = login.identity
        existing_user = await self._user_repository.get_by_auth_identity(
            provider=AuthProvider.SPOTIFY,
            subject=identity.subject,
        )

        if existing_user is None:
            raw_name = (identity.display_name or "").strip()
            display_name = raw_name or "Spotify-Nutzer"
            user = User.create(
                name=display_name,
                profile_image_url=identity.profile_image_url,
            )
            existing_user = await self._user_repository.create_with_auth_identity(
                user=user,
                auth_identity=AuthIdentity.create(
                    user_id=user.id,
                    provider=AuthProvider.SPOTIFY,
                    subject=identity.subject,
                ),
            )
        else:
            existing_user = await self._sync_profile_image(
                user=existing_user,
                profile_image_url=identity.profile_image_url,
            )

        try:
            await login.connect(user_id=existing_user.id)
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
