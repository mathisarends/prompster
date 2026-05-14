from backend.features.session.domain import Session
from backend.features.session.presentation.schemas import SessionResponse


def to_session_response(session: Session) -> SessionResponse:
    return SessionResponse(
        id=session.id,
        title=session.title,
        system_prompt=session.system_prompt,
        created_at=session.created_at,
    )
