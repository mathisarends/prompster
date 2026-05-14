from backend.features.session.application.ports.title_generator import (
    SessionTitleGenerator,
)
from backend.features.session.domain import Session, SessionRepository


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
        initial_prompt: str,
        system_prompt: str | None = None,
    ) -> Session:
        generated_title = await self._title_generator.generate(
            initial_prompt=initial_prompt
        )
        title = (generated_title.strip() or "New Session")[:120]
        session = Session.create_with_initial_prompt(
            title=title,
            initial_prompt=initial_prompt,
            system_prompt=system_prompt,
        )
        return await self._session_repository.create(session=session)
