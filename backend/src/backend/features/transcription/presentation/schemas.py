from enum import StrEnum
from typing import Annotated, Literal, Union

from pydantic import Field

from backend.presentation.schema import Schema


class ClientCommandType(StrEnum):
    FLUSH = "flush"
    STOP = "stop"


class ServerEventType(StrEnum):
    SESSION_CONNECTED = "session_connected"
    TRANSCRIPT_DELTA = "transcript_delta"
    TRANSCRIPT_COMPLETED = "transcript_completed"
    SPEECH_STARTED = "speech_started"
    SPEECH_STOPPED = "speech_stopped"
    TRANSCRIBER_ERROR = "transcriber_error"
    ERROR = "error"


class FlushCommand(Schema):
    type: Literal[ClientCommandType.FLUSH] = ClientCommandType.FLUSH


class StopCommand(Schema):
    type: Literal[ClientCommandType.STOP] = ClientCommandType.STOP


ClientCommand = Annotated[
    Union[FlushCommand, StopCommand],
    Field(discriminator="type"),
]


class SessionConnectedEventResponse(Schema):
    type: Literal[ServerEventType.SESSION_CONNECTED] = ServerEventType.SESSION_CONNECTED


class TranscriptDeltaEventResponse(Schema):
    type: Literal[ServerEventType.TRANSCRIPT_DELTA] = ServerEventType.TRANSCRIPT_DELTA
    delta: str
    item_id: str


class TranscriptCompletedEventResponse(Schema):
    type: Literal[ServerEventType.TRANSCRIPT_COMPLETED] = (
        ServerEventType.TRANSCRIPT_COMPLETED
    )
    transcript: str
    item_id: str


class SpeechStartedEventResponse(Schema):
    type: Literal[ServerEventType.SPEECH_STARTED] = ServerEventType.SPEECH_STARTED
    item_id: str
    audio_start_ms: int


class SpeechStoppedEventResponse(Schema):
    type: Literal[ServerEventType.SPEECH_STOPPED] = ServerEventType.SPEECH_STOPPED
    item_id: str
    audio_end_ms: int


class TranscriptionErrorDetailsResponse(Schema):
    type: str
    message: str


class TranscriberErrorEventResponse(Schema):
    type: Literal[ServerEventType.TRANSCRIBER_ERROR] = ServerEventType.TRANSCRIBER_ERROR
    error: TranscriptionErrorDetailsResponse


class SocketErrorEventResponse(Schema):
    type: Literal[ServerEventType.ERROR] = ServerEventType.ERROR
    message: str


TranscriptionServerEvent = Annotated[
    Union[
        SessionConnectedEventResponse,
        TranscriptDeltaEventResponse,
        TranscriptCompletedEventResponse,
        SpeechStartedEventResponse,
        SpeechStoppedEventResponse,
        TranscriberErrorEventResponse,
        SocketErrorEventResponse,
    ],
    Field(discriminator="type"),
]


class TranscriptionResponse(Schema):
    text: str
    language: str | None = None
