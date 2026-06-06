from dishka import Provider, Scope, provide

from backend.features.transcription.application import (
    AudioTranscriber,
    TranscriptionOptions,
    TranscriptionSessionFactory,
)
from backend.features.transcription.infrastructure.realtime_whisper_session import (
    RealtimeWhisperSessionFactory,
)
from backend.features.transcription.infrastructure.settings import (
    TranscriptionSettings,
)
from backend.features.transcription.infrastructure.transcriptify_transcriber import (
    TranscriptifyAudioTranscriber,
)


class TranscriptionProvider(Provider):
    @provide(scope=Scope.APP)
    def provide_transcription_settings(self) -> TranscriptionSettings:
        return TranscriptionSettings()

    @provide(scope=Scope.APP)
    def provide_transcription_options(
        self,
        settings: TranscriptionSettings,
    ) -> TranscriptionOptions:
        return TranscriptionOptions(
            language=settings.language,
            delay=settings.delay,
            noise_reduction=settings.noise_reduction,
            include_logprobs=settings.include_logprobs,
            provider=settings.provider,
        )

    @provide(scope=Scope.APP)
    def provide_transcription_session_factory(self) -> TranscriptionSessionFactory:
        return RealtimeWhisperSessionFactory()

    @provide(scope=Scope.APP)
    def provide_audio_transcriber(
        self,
        settings: TranscriptionSettings,
    ) -> AudioTranscriber:
        return TranscriptifyAudioTranscriber(
            model=settings.file_model,
            language=settings.language,
        )
