from uuid import UUID

from backend.features.session.application.ports.session_summary_query import (
    SessionSummary,
    SessionSummaryQuery,
)
from backend.features.session.domain import (
    PlaylistTrack,
    Session,
    SessionRepository,
)
from backend.shared.decorators import timed


class SessionService:
    def __init__(
        self,
        session_repository: SessionRepository,
        session_summary_query: SessionSummaryQuery,
    ) -> None:
        self._session_repository = session_repository
        self._session_summary_query = session_summary_query

    async def get_by_id(self, *, session_id: UUID, user_id: UUID) -> Session:
        return await self._get_authorized(session_id=session_id, user_id=user_id)

    @timed()
    async def create(self, *, owner_id: UUID, initial_prompt: str) -> Session:
        session = Session(
            title="",
            entries=[],
            owner_id=owner_id,
        )
        session = await self._session_repository.create(session=session)
        return session

    async def update(
        self, *, session_id: UUID, user_id: UUID, title: str | None = None
    ) -> Session:
        session = await self._get_authorized(session_id=session_id, user_id=user_id)
        return await self._session_repository.update(
            session_id=session.id,
            title=title,
        )

    async def delete(self, *, session_id: UUID, user_id: UUID) -> None:
        session = await self._get_authorized(session_id=session_id, user_id=user_id)
        await self._session_repository.delete(session_id=session.id)

    async def star(self, *, session_id: UUID, user_id: UUID) -> Session:
        session = await self._get_authorized(session_id=session_id, user_id=user_id)
        session.star()
        return await self._session_repository.save(session=session)

    async def unstar(self, *, session_id: UUID, user_id: UUID) -> Session:
        session = await self._get_authorized(session_id=session_id, user_id=user_id)
        session.unstar()
        return await self._session_repository.save(session=session)

    async def add_playlist_track(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        title: str,
        artist: str,
        year: int,
        spotify_uri: str | None = None,
        cover_url: str | None = None,
    ) -> PlaylistTrack:
        session = await self._get_authorized(session_id=session_id, user_id=user_id)
        track = session.add_track(
            title=title,
            artist=artist,
            year=year,
            spotify_uri=spotify_uri,
            cover_url=cover_url,
        )
        await self._session_repository.save(session=session)
        return track

    async def remove_playlist_track(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        track_id: UUID,
    ) -> None:
        session = await self._get_authorized(session_id=session_id, user_id=user_id)
        session.remove_track(track_id=track_id)
        await self._session_repository.save(session=session)

    async def restore_user_curation_event(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        event_id: UUID,
    ) -> Session:
        session = await self._get_authorized(session_id=session_id, user_id=user_id)
        session.restore_user_curation_event(event_id=event_id)
        return await self._session_repository.save(session=session)

    async def list(
        self,
        *,
        owner_id: UUID,
        limit: int,
        offset: int,
    ) -> list[SessionSummary]:
        return await self._session_summary_query.list_for_owner(
            owner_id=owner_id,
            limit=limit,
            offset=offset,
        )

    async def search(
        self,
        *,
        owner_id: UUID,
        query: str,
        limit: int,
        offset: int,
    ) -> list[SessionSummary]:
        return await self._session_summary_query.search_for_owner(
            owner_id=owner_id,
            query=query,
            limit=limit,
            offset=offset,
        )

    async def _get_authorized(self, *, session_id: UUID, user_id: UUID) -> Session:
        session = await self._session_repository.get_by_id(session_id=session_id)
        session.has_access(user_id)
        return session
