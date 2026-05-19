from collections.abc import AsyncIterator
from dataclasses import dataclass
from urllib.parse import quote_plus
from uuid import UUID

from backend.features.session.application.events import (
    SessionAssistantMessageChunk,
    SessionAssistantMessageCompleted,
    SessionAssistantMessageStarted,
    SessionEvent,
)
from backend.features.session.application.ports import (
    PlaylistDeckPdfRenderer,
    PlaylistDeckTrack,
)
from backend.features.session.application.ports.session_runner import SessionRunner
from backend.features.session.application.ports.session_summary_query import (
    SessionSummary,
    SessionSummaryQuery,
)
from backend.features.session.application.ports.title_generator import (
    SessionTitleGenerator,
)
from backend.features.session.domain import (
    PlaylistTrack,
    Session,
    SessionPlaylistEmptyError,
    SessionRepository,
)


@dataclass(frozen=True)
class CreateSessionResult:
    session: Session


@dataclass(frozen=True)
class FollowUpAnswer:
    question_id: UUID
    option_id: str | None
    text: str | None


class SessionService:
    def __init__(
        self,
        session_repository: SessionRepository,
        session_summary_query: SessionSummaryQuery,
        title_generator: SessionTitleGenerator,
        runner: SessionRunner,
        playlist_deck_pdf_renderer: PlaylistDeckPdfRenderer,
    ) -> None:
        self._session_repository = session_repository
        self._session_summary_query = session_summary_query
        self._title_generator = title_generator
        self._runner = runner
        self._playlist_deck_pdf_renderer = playlist_deck_pdf_renderer

    async def get_by_id(self, *, session_id: UUID, user_id: UUID) -> Session:
        return await self._get_authorized(session_id=session_id, user_id=user_id)

    async def create(
        self, *, owner_id: UUID, initial_prompt: str
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
        return CreateSessionResult(session=session)

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

    async def send_message(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        content: str,
    ) -> AsyncIterator[SessionEvent]:
        session = await self._get_authorized(session_id=session_id, user_id=user_id)
        self._prepare_follow_up_context_for_message(session=session)
        session.add_user_message(content=content)
        await self._session_repository.save(session=session)
        async for event in self._run_llm(session=session):
            yield event

    async def answer_follow_ups(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        answers: list[FollowUpAnswer],
    ) -> AsyncIterator[SessionEvent]:
        session = await self._get_authorized(session_id=session_id, user_id=user_id)
        for answer in answers:
            if answer.option_id is not None:
                session.answer_follow_up_with_option(
                    question_id=answer.question_id,
                    option_id=answer.option_id,
                )
            else:
                session.answer_follow_up_with_text(
                    question_id=answer.question_id,
                    text=answer.text or "",
                )
        await self._session_repository.save(session=session)
        async for event in self._run_llm(session=session):
            yield event

    async def skip_remaining_follow_ups(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
    ) -> AsyncIterator[SessionEvent]:
        session = await self._get_authorized(session_id=session_id, user_id=user_id)
        self._prepare_follow_up_context_for_message(session=session)
        await self._session_repository.save(session=session)
        async for event in self._run_llm(session=session):
            yield event

    async def add_playlist_track(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        title: str,
        artist: str,
        year: int | None = None,
        cover_url: str | None = None,
    ) -> PlaylistTrack:
        session = await self._get_authorized(session_id=session_id, user_id=user_id)
        track = session.add_track(
            title=title,
            artist=artist,
            year=year,
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

    async def export_playlist_pdf(self, *, session_id: UUID, user_id: UUID) -> bytes:
        session = await self._get_authorized(session_id=session_id, user_id=user_id)
        playlist = session.playlist
        if playlist is None or not playlist.tracks:
            raise SessionPlaylistEmptyError(
                f"Session {session.id} has no playlist tracks to export."
            )

        tracks = [self._to_deck_track(track) for track in playlist.tracks]
        return await self._playlist_deck_pdf_renderer.render(tracks=tracks)

    async def _get_authorized(self, *, session_id: UUID, user_id: UUID) -> Session:
        session = await self._session_repository.get_by_id(session_id=session_id)
        session.has_access(user_id)
        return session

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

    def _prepare_follow_up_context_for_message(
        self, *, session: Session
    ) -> UUID | None:
        pending_group = session.pending_follow_up_group()
        if pending_group is None:
            return None

        current_question = pending_group.current_question
        if current_question is None:
            return None

        session.skip_remaining_follow_ups(question_id=current_question.id)
        return pending_group.id

    async def _run_llm(self, *, session: Session) -> AsyncIterator[SessionEvent]:
        message = session.add_assistant_message()
        yield SessionAssistantMessageStarted(message=message)
        async for chunk in self._runner.run(session=session):
            session.append_to_current_assistant_message(chunk)
            yield SessionAssistantMessageChunk(message_id=message.id, chunk=chunk)
        await self._session_repository.save(session=session)
        yield SessionAssistantMessageCompleted(message=message)

    def _to_deck_track(self, track: PlaylistTrack) -> PlaylistDeckTrack:
        query = quote_plus(f"{track.title} {track.artist}".strip())
        spotify_search_url = f"https://open.spotify.com/search/{query}"
        year = str(track.year) if track.year is not None else ""
        return PlaylistDeckTrack(
            title=track.title,
            artist_names=track.artist,
            release_year=year,
            spotify_url=spotify_search_url,
        )
