from backend.features.auth.presentation.oauth_state_cookies import OAuthStateCookies


class SpotifyOAuthStateCookies(OAuthStateCookies):
    """OAuth state cookie for the Spotify connection flow.

    Subclass exists purely for DI type discrimination.
    """
