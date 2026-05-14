from datetime import UTC, datetime
from uuid import uuid4

from backend.features.session.domain import Session, SessionRepository


class CreateSessionHandler:
    def __init__(self, session_repository: SessionRepository) -> None:
        self._session_repository = session_repository

    async def handle(
        self,
        *,
        title: str,
        system_prompt: str | None = None,
    ) -> Session:
        now = datetime.now(UTC)
        session = Session(
            id=uuid4(),
            title=title,
            messages=[],
            system_prompt=system_prompt,
            created_time=now,
        )
        return await self._session_repository.create(session=session)
