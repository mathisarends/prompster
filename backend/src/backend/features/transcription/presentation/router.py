from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends, WebSocket

from backend.features.auth.presentation.dependencies import AuthenticatedUserId
from backend.features.transcription.application import (
    TranscriptionOptions,
    TranscriptionSessionFactory,
)
from backend.features.transcription.presentation.socket_handler import (
    RealtimeTranscriptionSocketHandler,
)
from backend.shared.dependencies import dishka_ws_dep

transcription_router = APIRouter(
    route_class=DishkaRoute,
    prefix="/transcription",
    tags=["transcription"],
)


def _build_socket_handler(
    options: Annotated[
        TranscriptionOptions,
        dishka_ws_dep(TranscriptionOptions),
    ],
    factory: Annotated[
        TranscriptionSessionFactory,
        dishka_ws_dep(TranscriptionSessionFactory),
    ],
) -> RealtimeTranscriptionSocketHandler:
    return RealtimeTranscriptionSocketHandler(
        session_factory=factory,
        default_options=options,
    )


@transcription_router.websocket("/realtime")
async def stream_realtime_transcription(
    websocket: WebSocket,
    _authenticated_user_id: AuthenticatedUserId,
    handler: Annotated[
        RealtimeTranscriptionSocketHandler,
        Depends(_build_socket_handler),
    ],
) -> None:
    await handler(websocket)
