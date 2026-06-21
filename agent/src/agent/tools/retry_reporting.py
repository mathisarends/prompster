"""Bridge spotifyify's synchronous retry hook to the agent's event stream.

spotifyify fires ``on_retry`` callbacks synchronously from deep inside an
awaited HTTP call — it cannot ``yield`` an :class:`~agent.events.AgentEvent`.
The agent loop installs a sink (via :func:`retry_sink`) for the duration of a
tool call; the tool handler's retry hook forwards every ``RetryEvent`` to that
sink with :func:`report_retry`. The loop drains those into ``ToolRetryEvent``s.

The sink lives in a :class:`~contextvars.ContextVar` so it propagates down the
``await`` chain (and into a tool ``Task`` whose context is copied at creation)
without threading a parameter through every handler method.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from spotifyify import RetryEvent

RetrySink = Callable[[RetryEvent], None]

_retry_sink: ContextVar[RetrySink | None] = ContextVar(
    "agent_spotify_retry_sink", default=None
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
