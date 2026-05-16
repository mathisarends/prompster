from backend.features.session.domain import Session


class GetSessionByIdHandler:
    async def handle(self, *, session: Session) -> Session:
        return session
