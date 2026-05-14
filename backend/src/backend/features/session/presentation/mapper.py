from backend.features.session.domain import Session
from backend.features.session.domain.views import SessionMessage
from backend.features.session.presentation.schemas import (
    MessageResponse,
    SessionResponse,
)


def to_session_response(session: Session) -> SessionResponse:
    return SessionResponse(
        id=session.id,
        title=session.title,
        system_prompt=session.system_prompt,
        created_at=session.created_at,
    )


def to_message_response(message: SessionMessage) -> MessageResponse:
    return MessageResponse(
        id=message.id,
        role=message.role,
        content=message.content,
        created_at=message.created_at,
    )
