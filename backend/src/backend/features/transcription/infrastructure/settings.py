from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from transcriptify import WhisperModel

from backend.features.transcription.application import (
    NoiseReduction,
    RealtimeProvider,
    TranscriptionDelay,
)


class TranscriptionSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="TRANSCRIPTION_",
    )

    language: str | None = Field(default=None, min_length=2, max_length=12)
    delay: TranscriptionDelay = TranscriptionDelay.MEDIUM
    noise_reduction: NoiseReduction = NoiseReduction.FAR_FIELD
    include_logprobs: bool = False
    provider: RealtimeProvider = RealtimeProvider.OPENAI
    file_model: WhisperModel = WhisperModel.GPT_4O_TRANSCRIBE
