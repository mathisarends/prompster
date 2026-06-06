from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    WebSocket,
    status,
)

from backend.features.auth.presentation.dependencies import AuthenticatedUserId
from backend.features.transcription.application import (
    AudioTranscriber,
    TranscriptionOptions,
    TranscriptionSessionFactory,
)
from backend.features.transcription.presentation.audio_encoding import (
    resolve_audio_encoding,
)
from backend.features.transcription.presentation.schemas import TranscriptionResponse
from backend.features.transcription.presentation.socket_handler import (
    RealtimeTranscriptionSocketHandler,
)
from backend.presentation.errors import ErrorDto
from backend.shared.dependencies import dishka_ws_dep

transcription_router = APIRouter(
    route_class=DishkaRoute,
    prefix="/transcription",
    tags=["transcription"],
)

_unauthorized = {status.HTTP_401_UNAUTHORIZED: {"model": ErrorDto}}


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


@transcription_router.post(
    "",
    response_model=TranscriptionResponse,
    status_code=status.HTTP_200_OK,
    operation_id="transcribe_audio",
    responses={
        **_unauthorized,
        status.HTTP_400_BAD_REQUEST: {"model": ErrorDto},
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: {"model": ErrorDto},
    },
)
async def transcribe_audio(
    _authenticated_user_id: AuthenticatedUserId,
    transcriber: FromDishka[AudioTranscriber],
    file: Annotated[UploadFile, File()],
) -> TranscriptionResponse:
    encoding = resolve_audio_encoding(file)

    data = await file.read()
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio file is empty.",
        )

    result = await transcriber.transcribe(data=data, encoding=encoding)
    return TranscriptionResponse(text=result.text, language=result.language)
