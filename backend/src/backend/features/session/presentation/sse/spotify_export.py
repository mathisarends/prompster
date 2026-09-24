"""Server-sent stream for exporting a session playlist to Spotify.

The export validates up front (in the route handler, via
``SessionSpotifyPlaylistExporter.prepare``) so domain errors still surface as
HTTP responses. Only the Spotify writes run here, inside the stream, so any
retries the Spotify client performs can be surfaced live as ``retry`` events
before the terminal ``completed``/``error`` and ``done`` events.
"""

import asyncio
import logging
from enum import StrEnum
from typing import Annotated, Literal, Union

from fastapi.responses import StreamingResponse
from pydantic import Field, RootModel, TypeAdapter
from spotifyify import RetryEvent

from backend.features.session.application import SessionSpotifyPlaylistExporter
from backend.features.session.application.spotify_playlist_exporter import (
    SpotifyExportPlan,
)
from backend.features.session.presentation.mapper import (
    to_spotify_playlist_export_response,
)
from backend.features.session.presentation.schemas import SpotifyPlaylistExportResponse
from backend.features.spotify.application.retry_reporting import retry_sink
from backend.presentation.schema import Schema

logger = logging.getLogger(__name__)


class SpotifyExportEventType(StrEnum):
    RETRY = "spotify_export.retry"
    COMPLETED = "spotify_export.completed"
    DONE = "done"
    ERROR = "error"


class _SpotifyExportEventSchema(Schema):
    type: SpotifyExportEventType


class SpotifyExportRetryEvent(_SpotifyExportEventSchema):
    type: Literal[SpotifyExportEventType.RETRY] = SpotifyExportEventType.RETRY
    attempt: int
    max_attempts: int
    retry_in_seconds: float | None = None


class SpotifyExportCompletedEvent(_SpotifyExportEventSchema):
    type: Literal[SpotifyExportEventType.COMPLETED] = SpotifyExportEventType.COMPLETED
    playlist: SpotifyPlaylistExportResponse


class SpotifyExportDoneEvent(_SpotifyExportEventSchema):
    type: Literal[SpotifyExportEventType.DONE] = SpotifyExportEventType.DONE


class SpotifyExportErrorEvent(_SpotifyExportEventSchema):
    type: Literal[SpotifyExportEventType.ERROR] = SpotifyExportEventType.ERROR
    code: str
    message: str


SpotifyExportServerEvent = Annotated[
    Union[
        SpotifyExportRetryEvent,
        SpotifyExportCompletedEvent,
        SpotifyExportDoneEvent,
        SpotifyExportErrorEvent,
    ],
    Field(discriminator="type"),
]


class SpotifyExportServerEventSchema(RootModel[SpotifyExportServerEvent | None]):
    """Schema-only model exposing the export event union for client generation."""


_EVENT_ADAPTER: TypeAdapter[SpotifyExportServerEvent] = TypeAdapter(
    SpotifyExportServerEvent
)


def stream_spotify_export(
    exporter: SessionSpotifyPlaylistExporter,
    plan: SpotifyExportPlan,
) -> StreamingResponse:
    return StreamingResponse(
        _stream(exporter, plan),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


async def _stream(
    exporter: SessionSpotifyPlaylistExporter,
    plan: SpotifyExportPlan,
):
    try:
        exported = None
        retries: asyncio.Queue[RetryEvent] = asyncio.Queue()
        with retry_sink(retries.put_nowait):
            exec_task = asyncio.create_task(exporter.execute(plan))
            while True:
                getter = asyncio.create_task(retries.get())
                done, _ = await asyncio.wait(
                    {exec_task, getter},
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if getter in done:
                    yield _to_sse(_to_retry_event(getter.result()))
                else:
                    getter.cancel()
                if exec_task in done:
                    break
            exported = exec_task.result()
            while not retries.empty():
                yield _to_sse(_to_retry_event(retries.get_nowait()))
        yield _to_sse(
            SpotifyExportCompletedEvent(
                playlist=to_spotify_playlist_export_response(exported)
            )
        )
    except Exception as exc:
        logger.exception("Unexpected error while exporting playlist to Spotify.")
        yield _to_sse(
            SpotifyExportErrorEvent(
                code=type(exc).__name__,
                message="Die Playlist konnte nicht zu Spotify exportiert werden.",
            )
        )
    yield _to_sse(SpotifyExportDoneEvent())


def _to_retry_event(event: RetryEvent) -> SpotifyExportRetryEvent:
    return SpotifyExportRetryEvent(
        attempt=event.retry_number,
        max_attempts=event.max_retries,
        retry_in_seconds=event.retry_in_seconds,
    )


def _to_sse(event: SpotifyExportServerEvent) -> str:
    event_name = event.type.value
    data = _EVENT_ADAPTER.dump_json(event, by_alias=True).decode()
    return f"event: {event_name}\ndata: {data}\n\n"
