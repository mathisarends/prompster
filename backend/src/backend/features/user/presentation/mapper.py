from backend.features.user.application import UserMeDto
from backend.features.user.presentation.schemas import UserMeResponse


def to_user_me_response(dto: UserMeDto) -> UserMeResponse:
    return UserMeResponse(
        id=dto.user.id,
        name=dto.user.name,
        email=dto.user.email,
        created_at=dto.user.created_at,
        spotify_connected=dto.spotify_connected,
    )
