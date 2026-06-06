import logging

from backend.env import LoggingLevelSettings

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

# Third-party libraries that emit very verbose DEBUG output (per-request headers,
# connection pool chatter, raw chunks). We pin them to WARNING so our own DEBUG
# logs stay readable even when the app runs at DEBUG in dev.
_NOISY_LOGGERS = (
    "httpx",
    "httpcore",
    "openai",
    "websockets",
    "websockets.client",
    "spotifyify",
    "urllib3",
    "asyncio",
)


def setup_logging(settings: LoggingLevelSettings) -> None:
    logging.basicConfig(
        level=settings.effective_log_level,
        format=_LOG_FORMAT,
    )
    logging.getLogger().setLevel(settings.effective_log_level)
    logging.getLogger("backend").setLevel(settings.effective_log_level)

    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
