from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request

from backend.features.auth.presentation.dependencies import AuthenticatedUserId
from backend.features.session.domain import Session, SessionRepository


async def _get_session_repository(request: Request) -> SessionRepository:
    return await request.state.dishka_container.get(SessionRepository)


async def _get_authorized_session(
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    session_repository: Annotated[SessionRepository, Depends(_get_session_repository)],
) -> Session:
    session = await session_repository.get_by_id(session_id=session_id)
    session.has_access(authenticated_user_id)
    return session


AuthorizedSession = Annotated[Session, Depends(_get_authorized_session)]
