from pydantic import TypeAdapter

from backend.features.transcription.application import (
    SessionConnected,
    SpeechStarted,
    SpeechStopped,
    TranscriptCompleted,
    TranscriptDelta,
    TranscriberError,
    TranscriptionEvent,
    TranscriptionOptions,
)
from backend.features.transcription.presentation.schemas import (
    ClientCommand,
    RealtimeTranscriptionOptionsQuery,
    SessionConnectedEventResponse,
    SocketErrorEventResponse,
    SpeechStartedEventResponse,
    SpeechStoppedEventResponse,
    TranscriptCompletedEventResponse,
    TranscriptDeltaEventResponse,
    TranscriberErrorEventResponse,
    TranscriptionErrorDetailsResponse,
    TranscriptionServerEvent,
)

_client_command_adapter = TypeAdapter(ClientCommand)


def parse_client_command(raw_message: str) -> ClientCommand:
    return _client_command_adapter.validate_json(raw_message)


def to_transcription_options(
    query: RealtimeTranscriptionOptionsQuery,
) -> TranscriptionOptions:
    return TranscriptionOptions(
        language=query.language,
        delay=query.delay,
        noise_reduction=query.noise_reduction,
        include_logprobs=query.include_logprobs,
        provider=query.provider,
    )


def to_transcription_server_event(
    event: TranscriptionEvent,
) -> TranscriptionServerEvent:
    match event:
        case SessionConnected():
            return SessionConnectedEventResponse()
        case TranscriptDelta(delta=delta, item_id=item_id):
            return TranscriptDeltaEventResponse(delta=delta, item_id=item_id)
        case TranscriptCompleted(transcript=transcript, item_id=item_id):
            return TranscriptCompletedEventResponse(
                transcript=transcript, item_id=item_id
            )
        case SpeechStarted(item_id=item_id, audio_start_ms=audio_start_ms):
            return SpeechStartedEventResponse(
                item_id=item_id,
                audio_start_ms=audio_start_ms,
            )
        case SpeechStopped(item_id=item_id, audio_end_ms=audio_end_ms):
            return SpeechStoppedEventResponse(
                item_id=item_id, audio_end_ms=audio_end_ms
            )
        case TranscriberError(error=error):
            return TranscriberErrorEventResponse(
                error=TranscriptionErrorDetailsResponse(
                    type=error.type,
                    message=error.message,
                )
            )


def to_socket_error_event(message: str) -> SocketErrorEventResponse:
    return SocketErrorEventResponse(message=message)
