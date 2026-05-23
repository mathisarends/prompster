import asyncio
from collections.abc import AsyncIterator

from realtime_whisper import (
    AzureOpenAIProvider,
    NoiseReduction as RealtimeNoiseReduction,
    OpenAIProvider,
    RealtimeTranscriber,
    SessionConnected as RealtimeSessionConnected,
    SpeechStarted as RealtimeSpeechStarted,
    SpeechStopped as RealtimeSpeechStopped,
    TranscriptCompleted as RealtimeTranscriptCompleted,
    TranscriptDelta as RealtimeTranscriptDelta,
    TranscriberError as RealtimeTranscriberError,
    TranscriptionDelay as RealtimeTranscriptionDelay,
)
from realtime_whisper.audio import AudioInputDevice

from backend.features.transcription.application import (
    NoiseReduction,
    RealtimeProvider,
    SessionConnected,
    SpeechStarted,
    SpeechStopped,
    TranscriptCompleted,
    TranscriptDelta,
    TranscriberError,
    TranscriptionDelay,
    TranscriptionErrorDetails,
    TranscriptionEvent,
    TranscriptionOptions,
    TranscriptionSession,
    TranscriptionSessionFactory,
)


class WebSocketAudioInput(AudioInputDevice):
    def __init__(self, *, max_queue_size: int = 128) -> None:
        self._queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=max_queue_size)
        self._active = False

    @property
    def is_active(self) -> bool:
        return self._active

    async def start(self) -> None:
        self._active = True

    async def stop(self) -> None:
        if not self._active:
            return

        self._active = False
        self._queue_shutdown_marker()

    async def enqueue_chunk(self, chunk: bytes) -> None:
        if not chunk:
            return

        await self._queue.put(chunk)

    async def stream_chunks(self) -> AsyncIterator[bytes]:
        while True:
            chunk = await self._queue.get()
            if chunk is None:
                return
            yield chunk

    def _queue_shutdown_marker(self) -> None:
        try:
            self._queue.put_nowait(None)
        except asyncio.QueueFull:
            _ = self._queue.get_nowait()
            self._queue.put_nowait(None)


class RealtimeWhisperSession(TranscriptionSession):
    def __init__(
        self,
        *,
        transcriber: RealtimeTranscriber,
        audio_input: WebSocketAudioInput,
    ) -> None:
        self._transcriber = transcriber
        self._audio_input = audio_input

    def stream(self) -> AsyncIterator[TranscriptionEvent]:
        return self._stream_events()

    async def push_audio_chunk(self, chunk: bytes) -> None:
        await self._audio_input.enqueue_chunk(chunk)

    async def flush(self) -> None:
        await self._transcriber.flush()

    async def stop(self) -> None:
        await self._transcriber.stop()

    async def _stream_events(self) -> AsyncIterator[TranscriptionEvent]:
        async for event in self._transcriber.stream():
            yield _to_transcription_event(event)


class RealtimeWhisperSessionFactory(TranscriptionSessionFactory):
    def create(self, *, options: TranscriptionOptions) -> TranscriptionSession:
        audio_input = WebSocketAudioInput()
        transcriber = RealtimeTranscriber(
            language=options.language,
            delay=_to_realtime_delay(options.delay),
            noise_reduction=_to_realtime_noise_reduction(options.noise_reduction),
            include_logprobs=options.include_logprobs,
            audio_input=audio_input,
            provider=_to_realtime_provider(options.provider),
        )

        return RealtimeWhisperSession(
            transcriber=transcriber,
            audio_input=audio_input,
        )


def _to_realtime_delay(delay: TranscriptionDelay) -> RealtimeTranscriptionDelay:
    match delay:
        case TranscriptionDelay.MINIMAL:
            return RealtimeTranscriptionDelay.MINIMAL
        case TranscriptionDelay.LOW:
            return RealtimeTranscriptionDelay.LOW
        case TranscriptionDelay.MEDIUM:
            return RealtimeTranscriptionDelay.MEDIUM
        case TranscriptionDelay.HIGH:
            return RealtimeTranscriptionDelay.HIGH
        case TranscriptionDelay.XHIGH:
            return RealtimeTranscriptionDelay.XHIGH


def _to_realtime_noise_reduction(
    noise_reduction: NoiseReduction,
) -> RealtimeNoiseReduction:
    match noise_reduction:
        case NoiseReduction.NEAR_FIELD:
            return RealtimeNoiseReduction.NEAR_FIELD
        case NoiseReduction.FAR_FIELD:
            return RealtimeNoiseReduction.FAR_FIELD


def _to_realtime_provider(provider: RealtimeProvider):
    if provider == RealtimeProvider.AZURE:
        return AzureOpenAIProvider()
    return OpenAIProvider()


def _to_transcription_event(event) -> TranscriptionEvent:
    match event:
        case RealtimeSessionConnected():
            return SessionConnected()
        case RealtimeTranscriptDelta(delta=delta, item_id=item_id):
            return TranscriptDelta(delta=delta, item_id=item_id)
        case RealtimeTranscriptCompleted(transcript=transcript, item_id=item_id):
            return TranscriptCompleted(transcript=transcript, item_id=item_id)
        case RealtimeSpeechStarted(item_id=item_id, audio_start_ms=audio_start_ms):
            return SpeechStarted(item_id=item_id, audio_start_ms=audio_start_ms)
        case RealtimeSpeechStopped(item_id=item_id, audio_end_ms=audio_end_ms):
            return SpeechStopped(item_id=item_id, audio_end_ms=audio_end_ms)
        case RealtimeTranscriberError(error=error):
            return TranscriberError(
                error=TranscriptionErrorDetails(
                    type=error.type,
                    message=error.message,
                )
            )
