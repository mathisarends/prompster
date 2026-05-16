from backend.features.auth.application.exceptions import InvalidCredentialsException
from backend.features.auth.application.ports import GoogleOAuthProvider, TokenIssuer
from backend.features.auth.application.schemas import AuthSession
from backend.features.user.domain import User, UserRepository


class GoogleCallbackHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        google_oauth_provider: GoogleOAuthProvider,
        token_issuer: TokenIssuer,
    ) -> None:
        self._user_repository = user_repository
        self._google_oauth_provider = google_oauth_provider
        self._token_issuer = token_issuer

    async def handle(self, *, authorization_code: str) -> AuthSession:
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
        existing_user = await self._user_repository.get_by_email(email=normalized_email)

        if existing_user is None:
            raw_name = (identity.name or "").strip()
            fallback_name = normalized_email.split("@", maxsplit=1)[0]
            display_name = raw_name or fallback_name
            existing_user = await self._user_repository.create(
                user=User(
                    name=display_name,
                    email=normalized_email,
                    google_subject=identity.subject,
                )
            )

        if existing_user.google_subject != identity.subject:
            raise InvalidCredentialsException("Google account does not match user")

        return self._token_issuer.create_session(user_id=existing_user.id)
