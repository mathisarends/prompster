from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models import Model

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

    def __init__(self, llm: Model) -> None:
        self._llm = llm
        self._agent = Agent(
            llm,
            instructions=self._SYSTEM_PROMPT,
            output_type=_PlaylistMetadataOutput,
        )

    async def generate(self, tracks: list[PlaylistMetadataTrack]) -> PlaylistMetadata:
        # Holding the model context keeps its shared client open during this call.
        async with self._llm:
            result = await self._agent.run(self._format_tracks(tracks))
        metadata = result.output
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
