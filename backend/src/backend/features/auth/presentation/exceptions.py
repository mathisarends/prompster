class AuthenticationRequiredError(Exception):
    """Raised when an HTTP request has no usable authentication session."""
