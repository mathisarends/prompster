from uuid import UUID

from backend.features.session.application.exceptions import (
    SessionNotFoundApplicationError,
    SessionUpdateValidationError,
)
from backend.features.session.domain import (
    Session,
    SessionNotFoundError,
    SessionRepository,
)


class UpdateSessionHandler:
    def __init__(self, session_repository: SessionRepository) -> None:
        self._session_repository = session_repository

    async def handle(
        self,
        *,
        session_id: UUID,
        title: str | None = None,
        system_prompt: str | None = None,
    ) -> Session:
        if title is None and system_prompt is None:
            raise SessionUpdateValidationError(
                "At least one field must be provided for update"
            )

        try:
            updated_session = await self._session_repository.update(
                session_id=session_id,
                title=title,
                system_prompt=system_prompt,
            )
        except SessionNotFoundError as exc:
            raise SessionNotFoundApplicationError from exc

        return updated_session
