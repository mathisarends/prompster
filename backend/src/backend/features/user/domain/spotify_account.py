from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True, slots=True)
class SpotifyAccount:
    connected: bool
    is_premium: bool

    @classmethod
    def disconnected(cls) -> Self:
        return cls(connected=False, is_premium=False)

    @classmethod
    def connected_with(cls, *, is_premium: bool) -> Self:
        return cls(connected=True, is_premium=is_premium)
