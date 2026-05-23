from backend.presentation.feature import Feature

from .infrastructure.di import TranscriptionProvider
from .presentation import transcription_router

feature = Feature(
    name="transcription",
    routers=[transcription_router],
    providers=[TranscriptionProvider],
)

__all__ = ["feature"]
