from dataclasses import dataclass

from backend.features.user.domain import User


@dataclass(frozen=True)
class UserMeDto:
    user: User
    spotify_connected: bool
