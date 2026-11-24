from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

from harnessed.events import TransientEvent


class ResearchEventKind(StrEnum):
    TRACKS_FOUND = "research.tracks.found"
    PLAYLISTS_FOUND = "research.playlists.found"
    SPOTIFY_RETRY = "research.spotify.retry"


@dataclass(frozen=True, slots=True)
class FoundTrack:
    """A Spotify track a research tool showed the model, addable by its URI."""

    uri: str
    title: str
    artist: str
    year: int | None = None
    cover_url: str | None = None


@dataclass(frozen=True, slots=True)
class FoundPlaylist:
    id: str
    name: str
    cover_url: str | None = None


@dataclass(frozen=True, slots=True)
class TracksFoundEvent(TransientEvent):
    """A research tool returned these tracks to the model."""

    call_id: str
    tracks: tuple[FoundTrack, ...]
    type: Literal[ResearchEventKind.TRACKS_FOUND] = field(
        default=ResearchEventKind.TRACKS_FOUND, kw_only=True
    )


@dataclass(frozen=True, slots=True)
class PlaylistsFoundEvent(TransientEvent):
    """A playlist search returned these playlists to the model."""

    call_id: str
    playlists: tuple[FoundPlaylist, ...]
    type: Literal[ResearchEventKind.PLAYLISTS_FOUND] = field(
        default=ResearchEventKind.PLAYLISTS_FOUND, kw_only=True
    )


@dataclass(frozen=True, slots=True)
class SpotifyRetryEvent(TransientEvent):
    """Spotify throttled a still-running tool call, which retries after a delay."""

    call_id: str
    tool_name: str
    attempt: int
    max_attempts: int
    retry_in_seconds: float | None = None
    status_code: int | None = None
    type: Literal[ResearchEventKind.SPOTIFY_RETRY] = field(
        default=ResearchEventKind.SPOTIFY_RETRY, kw_only=True
    )


RESEARCH_EVENTS = (TracksFoundEvent, PlaylistsFoundEvent, SpotifyRetryEvent)
