from collections.abc import AsyncIterator
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class TranscriptionDelay(StrEnum):
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"


class NoiseReduction(StrEnum):
    NEAR_FIELD = "near_field"
    FAR_FIELD = "far_field"


class RealtimeProvider(StrEnum):
    OPENAI = "openai"
    AZURE = "azure"


@dataclass(frozen=True)
class TranscriptionOptions:
    language: str | None = None
    delay: TranscriptionDelay = TranscriptionDelay.MEDIUM
    noise_reduction: NoiseReduction = NoiseReduction.FAR_FIELD
    include_logprobs: bool = False
    provider: RealtimeProvider = RealtimeProvider.OPENAI


@dataclass(frozen=True)
class SessionConnected:
    pass


@dataclass(frozen=True)
class TranscriptDelta:
    delta: str
    item_id: str


@dataclass(frozen=True)
class TranscriptCompleted:
    transcript: str
    item_id: str


@dataclass(frozen=True)
class SpeechStarted:
    item_id: str
    audio_start_ms: int


@dataclass(frozen=True)
class SpeechStopped:
    item_id: str
    audio_end_ms: int


@dataclass(frozen=True)
class TranscriptionErrorDetails:
    type: str
    message: str


@dataclass(frozen=True)
class TranscriberError:
    error: TranscriptionErrorDetails


type TranscriptionEvent = (
    SessionConnected
    | TranscriptDelta
    | TranscriptCompleted
    | SpeechStarted
    | SpeechStopped
    | TranscriberError
)


class TranscriptionSession(Protocol):
    def stream(self) -> AsyncIterator[TranscriptionEvent]: ...

    async def push_audio_chunk(self, chunk: bytes) -> None: ...

    async def flush(self) -> None: ...

    async def stop(self) -> None: ...


class TranscriptionSessionFactory(Protocol):
    def create(self, *, options: TranscriptionOptions) -> TranscriptionSession: ...
