from backend.features.auth.presentation.exceptions import AUTH_ERRORS
from fastapi_canon import ErrorRegistry

SPOTIFY_ERRORS = ErrorRegistry.merge(AUTH_ERRORS, name="spotify")
