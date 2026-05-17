from dataclasses import dataclass
from uuid import UUID

from backend.features.session.application.events import (
    SessionEvent,
    SessionTitleGenerated,
)
from backend.features.session.application.ports.title_generator import (
    SessionTitleGenerator,
)
from backend.features.session.domain import Session, SessionRepository


@dataclass(frozen=True)
class CreateSessionResult:
    session: Session
    events: tuple[SessionEvent, ...]


class CreateSessionHandler:
    def __init__(
        self,
        session_repository: SessionRepository,
        title_generator: SessionTitleGenerator,
    ) -> None:
        self._session_repository = session_repository
        self._title_generator = title_generator

    async def handle(
        self,
        *,
        owner_id: UUID,
        initial_prompt: str,
    ) -> CreateSessionResult:
        generated_title = await self._title_generator.generate(
            initial_prompt=initial_prompt
        )
        title = (generated_title.strip() or "New Session")[:120]
        session = Session.create_with_initial_prompt(
            title=title,
            initial_prompt=initial_prompt,
            owner_id=owner_id,
        )
        session = await self._session_repository.create(session=session)
        return CreateSessionResult(
            session=session,
            events=(SessionTitleGenerated(session_id=session.id, title=session.title),),
        )
