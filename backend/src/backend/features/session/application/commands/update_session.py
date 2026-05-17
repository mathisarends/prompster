from backend.features.session.domain import Session, SessionRepository


class UpdateSessionHandler:
    def __init__(self, session_repository: SessionRepository) -> None:
        self._session_repository = session_repository

    async def handle(
        self,
        *,
        session: Session,
        title: str | None = None,
    ) -> Session:
        return await self._session_repository.update(
            session_id=session.id,
            title=title,
        )
