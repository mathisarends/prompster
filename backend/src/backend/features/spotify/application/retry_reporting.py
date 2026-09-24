"""Bridge spotifyify's synchronous retry hook to a streaming response.

spotifyify fires ``on_retry`` callbacks synchronously from deep inside an
awaited HTTP call. A streaming endpoint installs a sink (via :func:`retry_sink`)
for the duration of the work; the playlist-creator adapter forwards every
``RetryEvent`` to that sink with :func:`report_retry`, and the endpoint drains
them into server-sent events.

The sink lives in a :class:`~contextvars.ContextVar` so it propagates down the
``await`` chain (and into a worker ``Task`` whose context is copied at creation)
without threading a callback through the application layer.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from spotifyify import RetryEvent

RetrySink = Callable[[RetryEvent], None]

_retry_sink: ContextVar[RetrySink | None] = ContextVar(
    "spotify_retry_sink", default=None
)


def report_retry(event: RetryEvent) -> None:
    """Forward a retry to the active sink, if one is installed."""
    sink = _retry_sink.get()
    if sink is not None:
        sink(event)


@contextmanager
def retry_sink(sink: RetrySink) -> Iterator[None]:
    """Install ``sink`` as the active retry sink for the duration of the block."""
    token = _retry_sink.set(sink)
    try:
        yield
    finally:
        _retry_sink.reset(token)
