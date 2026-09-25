class ServiceNotReadyException(Exception):
    """Raised when a dependency required to serve traffic is unavailable."""
