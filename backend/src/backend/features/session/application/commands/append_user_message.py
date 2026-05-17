from backend.features.session.application.events import (
    SessionEvent,
    SessionUserMessageAppended,
)
from backend.features.session.domain import Session


class AppendUserMessageHandler:
    async def handle(
        self, *, session: Session, content: str
    ) -> tuple[SessionEvent, ...]:
        message = session.add_user_message(content=content)
        return (SessionUserMessageAppended(message=message),)
