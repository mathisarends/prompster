import asyncio
import logging
from collections.abc import AsyncGenerator
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from backend.features.session.application import SessionSpotifyPlaylistExporter
from backend.features.session.domain import (
    SessionAccessDeniedError,
    SessionExportRequiresSpotifyConnectionError,
    SessionNotFoundError,
    SessionPlaylistEmptyError,
    SessionPlaylistMissingSpotifyTracksError,
)
from backend.features.session.presentation.mapper import (
    to_spotify_playlist_export_response,
)
from backend.features.session.presentation.schemas import SpotifyPlaylistExportResponse
from backend.features.spotify.application.retry_reporting import retry_sink
from pydantic import Field
from fastapi_canon.integrations.websockets import RpcModel
from spotifyify import RetryEvent

logger = logging.getLogger(__name__)

_EXPORT_ERRORS = (
    SessionAccessDeniedError,
    SessionExportRequiresSpotifyConnectionError,
    SessionNotFoundError,
    SessionPlaylistEmptyError,
    SessionPlaylistMissingSpotifyTracksError,
)


class SpotifyExportEventType(StrEnum):
    RETRY = "spotify_export.retry"
    COMPLETED = "spotify_export.completed"
    DONE = "done"
    ERROR = "error"


class _SpotifyExportEventSchema(RpcModel):
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


type SpotifyExportEvent = Annotated[
    SpotifyExportRetryEvent
    | SpotifyExportCompletedEvent
    | SpotifyExportDoneEvent
    | SpotifyExportErrorEvent,
    Field(discriminator="type"),
]


async def spotify_export_events(
    exporter: SessionSpotifyPlaylistExporter,
    *,
    session_id: UUID,
    user_id: UUID,
) -> AsyncGenerator[SpotifyExportEvent]:
    execution: asyncio.Task | None = None
    getter: asyncio.Task | None = None
    try:
        plan = await exporter.prepare(session_id=session_id, user_id=user_id)
        retries: asyncio.Queue[RetryEvent] = asyncio.Queue()
        with retry_sink(retries.put_nowait):
            execution = asyncio.create_task(exporter.execute(plan))
            while not execution.done():
                getter = asyncio.create_task(retries.get())
                done, _ = await asyncio.wait(
                    {execution, getter}, return_when=asyncio.FIRST_COMPLETED
                )
                if getter in done:
                    yield _to_retry_event(getter.result())
                else:
                    getter.cancel()
                    await asyncio.gather(getter, return_exceptions=True)
            exported = execution.result()
            while not retries.empty():
                yield _to_retry_event(retries.get_nowait())
        yield SpotifyExportCompletedEvent(
            playlist=to_spotify_playlist_export_response(exported)
        )
    except _EXPORT_ERRORS as exc:
        yield SpotifyExportErrorEvent(
            code=type(exc).__name__, message=str(exc) or type(exc).__name__
        )
    except Exception:
        logger.exception("Unexpected error while exporting playlist to Spotify.")
        yield SpotifyExportErrorEvent(
            code="InternalError",
            message="Die Playlist konnte nicht zu Spotify exportiert werden.",
        )
    finally:
        if getter is not None and not getter.done():
            getter.cancel()
            await asyncio.gather(getter, return_exceptions=True)
        if execution is not None and not execution.done():
            execution.cancel()
            await asyncio.gather(execution, return_exceptions=True)
    yield SpotifyExportDoneEvent()


def _to_retry_event(event: RetryEvent) -> SpotifyExportRetryEvent:
    return SpotifyExportRetryEvent(
        attempt=event.retry_number,
        max_attempts=event.max_retries,
        retry_in_seconds=event.retry_in_seconds,
    )
