from pathlib import PurePosixPath

from fastapi import HTTPException, UploadFile, status

# OpenAI accepts these audio container formats; the encoding is used as the
# uploaded file's extension so the backend can detect the format.
_SUPPORTED_ENCODINGS = frozenset(
    {"flac", "m4a", "mp3", "mp4", "mpeg", "mpga", "oga", "ogg", "wav", "webm"}
)
_CONTENT_TYPE_ENCODINGS = {
    "audio/flac": "flac",
    "audio/mp4": "m4a",
    "audio/x-m4a": "m4a",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/ogg": "ogg",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/wave": "wav",
    "audio/webm": "webm",
}


def resolve_audio_encoding(file: UploadFile) -> str:
    """Determine the audio container format of an uploaded recording.

    Prefers the filename extension and falls back to the content type. Raises
    a 415 if the format is not one OpenAI can transcribe.
    """
    if file.filename:
        suffix = PurePosixPath(file.filename).suffix.lstrip(".").lower()
        if suffix in _SUPPORTED_ENCODINGS:
            return suffix

    content_type = (file.content_type or "").split(";")[0].strip().lower()
    encoding = _CONTENT_TYPE_ENCODINGS.get(content_type)
    if encoding is not None:
        return encoding

    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail=(
            "Unsupported audio format. Supported formats: "
            f"{', '.join(sorted(_SUPPORTED_ENCODINGS))}."
        ),
    )
