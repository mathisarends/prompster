from callm import ChatModel, SystemMessage, UserMessage
from pydantic import BaseModel, Field

from backend.features.session.application.ports import (
    PlaylistMetadata,
    PlaylistMetadataGenerator,
    PlaylistMetadataTrack,
)


class _PlaylistMetadataOutput(BaseModel):
    name: str = Field(..., max_length=100)
    description: str = Field(..., max_length=300)


class LLMPlaylistMetadataGenerator(PlaylistMetadataGenerator):
    _SYSTEM_PROMPT = (
        "You craft Spotify playlist metadata. Given a list of tracks, return a "
        "concise, evocative playlist name (max 5 words) and a single-sentence "
        "description (max 300 characters) that captures the mood, theme, or era. "
        "Do not enumerate the tracks. Respond in the user's language."
    )

    def __init__(self, llm: ChatModel) -> None:
        self._llm = llm

    async def generate(self, tracks: list[PlaylistMetadataTrack]) -> PlaylistMetadata:
        output = await self._llm.call(
            [
                SystemMessage(content=self._SYSTEM_PROMPT),
                UserMessage(content=self._format_tracks(tracks)),
            ],
            output_format=_PlaylistMetadataOutput,
        )
        metadata = output.completion
        return PlaylistMetadata(
            name=metadata.name.strip(),
            description=metadata.description.strip(),
        )

    def _format_tracks(self, tracks: list[PlaylistMetadataTrack]) -> str:
        lines = []
        for track in tracks:
            year = f" ({track.year})"
            lines.append(f"- {track.title} — {track.artist}{year}")
        return "\n".join(lines)
