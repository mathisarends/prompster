from backend.features.user.domain import User
from backend.features.user.presentation.schemas import UserMeResponse


def to_user_me_response(user: User) -> UserMeResponse:
    return UserMeResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        created_at=user.created_at,
        spotify_connected=user.spotify.connected,
        spotify_premium=user.spotify.is_premium,
    )
