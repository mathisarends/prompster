from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends, Query, WebSocket
from starlette.requests import HTTPConnection

from backend.features.auth.presentation.dependencies import AuthenticatedUserId
from backend.features.transcription.application import (
    NoiseReduction,
    RealtimeProvider,
    TranscriptionDelay,
    TranscriptionSessionFactory,
)
from backend.features.transcription.presentation.mapper import to_transcription_options
from backend.features.transcription.presentation.schemas import (
    RealtimeTranscriptionOptionsQuery,
)
from backend.features.transcription.presentation.socket_handler import (
    RealtimeTranscriptionSocketHandler,
)

transcription_router = APIRouter(
    route_class=DishkaRoute,
    prefix="/transcription",
    tags=["transcription"],
)


async def _get_transcription_session_factory(
    conn: HTTPConnection,
) -> TranscriptionSessionFactory:
    return await conn.state.dishka_container.get(TranscriptionSessionFactory)


def _build_socket_handler(
    factory: Annotated[
        TranscriptionSessionFactory,
        Depends(_get_transcription_session_factory),
    ],
) -> RealtimeTranscriptionSocketHandler:
    return RealtimeTranscriptionSocketHandler(session_factory=factory)


@transcription_router.websocket("/realtime")
async def stream_realtime_transcription(
    websocket: WebSocket,
    _authenticated_user_id: AuthenticatedUserId,
    handler: Annotated[
        RealtimeTranscriptionSocketHandler,
        Depends(_build_socket_handler),
    ],
    language: str | None = Query(default=None, min_length=2, max_length=12),
    delay: TranscriptionDelay = Query(default=TranscriptionDelay.MEDIUM),
    noise_reduction: NoiseReduction = Query(default=NoiseReduction.FAR_FIELD),
    include_logprobs: bool = Query(default=False),
    provider: RealtimeProvider = Query(default=RealtimeProvider.OPENAI),
) -> None:
    options = to_transcription_options(
        RealtimeTranscriptionOptionsQuery(
            language=language,
            delay=delay,
            noise_reduction=noise_reduction,
            include_logprobs=include_logprobs,
            provider=provider,
        )
    )
    await handler.handle(websocket=websocket, options=options)
