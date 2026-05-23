from dishka import Provider, Scope, provide

from backend.features.transcription.application import TranscriptionSessionFactory
from backend.features.transcription.infrastructure.realtime_whisper_session import (
    RealtimeWhisperSessionFactory,
)


class TranscriptionProvider(Provider):
    @provide(scope=Scope.APP)
    def provide_transcription_session_factory(self) -> TranscriptionSessionFactory:
        return RealtimeWhisperSessionFactory()
