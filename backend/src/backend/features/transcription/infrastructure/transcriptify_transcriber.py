from transcriptify import (
    AudioChunk,
    OpenAIWhisper,
    ResponseFormat,
    WhisperModel,
)

from backend.features.transcription.application import (
    AudioTranscriber,
    TranscriptionResult,
)


class TranscriptifyAudioTranscriber(AudioTranscriber):
    def __init__(
        self,
        *,
        model: WhisperModel,
        language: str | None = None,
    ) -> None:
        self._whisper = OpenAIWhisper(
            model=model,
            language=language,
            response_format=ResponseFormat.JSON,
        )

    async def transcribe(self, *, data: bytes, encoding: str) -> TranscriptionResult:
        audio = AudioChunk(data=data, encoding=encoding)
        result = await self._whisper.transcribe(audio)
        return TranscriptionResult(text=result.text, language=result.language)
