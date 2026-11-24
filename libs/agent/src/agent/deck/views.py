from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DeckTrack:
    id: str
    title: str
    artist: str
    year: int | None = None
    spotify_uri: str | None = None
    cover_url: str | None = None


@dataclass(frozen=True, slots=True)
class Deck:
    id: str
    name: str
    tracks: tuple[DeckTrack, ...] = ()


@dataclass(frozen=True, slots=True)
class TrackReplacement:
    track_id: str
    track: DeckTrack
