import secrets

from backend.features.auth.application.exceptions import InvalidCredentialsException
from backend.features.auth.application.ports import GoogleOAuthProvider, TokenIssuer
from backend.features.auth.application.schemas import (
    AuthSession,
    GoogleAuthorizationRequest,
    GoogleCallbackResult,
)
from backend.features.user.domain import (
    AuthIdentity,
    AuthProvider,
    User,
    UserRepository,
)


class GoogleOAuthFlow:
    _STATE_TOKEN_BYTES = 32

    def __init__(
        self,
        user_repository: UserRepository,
        google_oauth_provider: GoogleOAuthProvider,
        token_issuer: TokenIssuer,
    ) -> None:
        self._user_repository = user_repository
        self._google_oauth_provider = google_oauth_provider
        self._token_issuer = token_issuer

    def login(self) -> GoogleAuthorizationRequest:
        oauth_state = secrets.token_urlsafe(self._STATE_TOKEN_BYTES)
        authorization_url = self._google_oauth_provider.build_authorization_url(
            state=oauth_state,
        )

        return GoogleAuthorizationRequest(
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
    ) -> GoogleCallbackResult:
        if error is not None:
            return GoogleCallbackResult.error(reason=error)

        if code is None:
            return GoogleCallbackResult.error(reason="missing_code")

        try:
            auth_session = await self._create_auth_session(
                authorization_code=code,
                oauth_state=state,
                expected_oauth_state=expected_oauth_state,
            )
        except InvalidCredentialsException:
            return GoogleCallbackResult.error(reason="invalid_credentials")

        return GoogleCallbackResult.success(session=auth_session)

    async def _create_auth_session(
        self,
        *,
        authorization_code: str,
        oauth_state: str,
        expected_oauth_state: str | None,
    ) -> AuthSession:
        if expected_oauth_state is None or not secrets.compare_digest(
            expected_oauth_state,
            oauth_state,
        ):
            raise InvalidCredentialsException("Invalid or missing OAuth state")

        try:
            identity = await self._google_oauth_provider.exchange_code_for_identity(
                authorization_code=authorization_code,
            )
        except ValueError as exc:
            raise InvalidCredentialsException(
                "Invalid Google authorization code"
            ) from exc

        if not identity.email_verified:
            raise InvalidCredentialsException("Google account email is not verified")

        normalized_email = identity.email.strip().lower()
        existing_user = await self._user_repository.get_by_auth_identity(
            provider=AuthProvider.GOOGLE,
            subject=identity.subject,
        )

        if existing_user is None:
            email_user = await self._user_repository.get_by_email(
                email=normalized_email
            )
            if email_user is not None:
                raise InvalidCredentialsException(
                    "Email already belongs to another auth identity"
                )

            raw_name = (identity.name or "").strip()
            fallback_name = normalized_email.split("@", maxsplit=1)[0]
            display_name = raw_name or fallback_name
            user = User(
                name=display_name,
                email=normalized_email,
            )
            existing_user = await self._user_repository.create_with_auth_identity(
                user=user,
                auth_identity=AuthIdentity(
                    user_id=user.id,
                    provider=AuthProvider.GOOGLE,
                    subject=identity.subject,
                ),
            )

        return self._token_issuer.create_session(user_id=existing_user.id)
