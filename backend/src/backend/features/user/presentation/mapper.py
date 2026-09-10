from backend.features.user.application import UserMessageRateLimitSnapshot
from backend.features.user.domain import User
from backend.features.user.presentation.schemas import (
    UserMeResponse,
    UserMessageRateLimitResponse,
)


def to_user_me_response(
    user: User,
    message_rate_limit: UserMessageRateLimitSnapshot,
) -> UserMeResponse:
    return UserMeResponse(
        id=user.id,
        name=user.name,
        created_at=user.created_at,
        spotify_connected=user.spotify.connected,
        spotify_premium=user.spotify.is_premium,
        message_rate_limit=UserMessageRateLimitResponse(
            limit=message_rate_limit.limit,
            remaining=message_rate_limit.remaining,
            reset_at=message_rate_limit.reset_at,
        ),
    )
