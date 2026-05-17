import secrets

from backend.features.auth.application.ports import GoogleOAuthProvider
from backend.features.auth.application.schemas import GoogleAuthorizationRequest


class GoogleLoginHandler:
    _STATE_TOKEN_BYTES = 32

    def __init__(self, google_oauth_provider: GoogleOAuthProvider) -> None:
        self._google_oauth_provider = google_oauth_provider

    def handle(self) -> GoogleAuthorizationRequest:
        oauth_state = secrets.token_urlsafe(self._STATE_TOKEN_BYTES)
        authorization_url = self._google_oauth_provider.build_authorization_url(
            state=oauth_state,
        )

        return GoogleAuthorizationRequest(
            authorization_url=authorization_url,
            state=oauth_state,
        )
