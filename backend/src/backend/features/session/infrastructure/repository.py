from datetime import datetime
from uuid import UUID

from backend.features.session.infrastructure.orm import (
    PlaylistTrackEntity,
    SessionEntity,
    SessionMessageEntity,
    SessionPlaylistEntity,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.features.session.domain import (
    FollowUpOption,
    FollowUpQuestion,
    FollowUpQuestionGroup,
    FollowUpQuestionState,
    MessageRole,
    Playlist,
    PlaylistTrack,
    Session,
    SessionMessage,
    SessionNotFoundError,
    SessionRepository,
    ToolCall,
    ToolCallGroup,
    ToolCallState,
    ToolFunction,
)
from backend.infrastructure.database.repository import Repository


class SqlSessionRepository(Repository[SessionEntity, Session], SessionRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=SessionEntity)

    def _to_domain(self, orm: SessionEntity) -> Session:
        messages = sorted(orm.messages, key=lambda item: item.position)
        return Session(
            id=orm.id,
            title=orm.title,
            messages=[self._to_domain_message(message) for message in messages],
            owner_id=orm.owner_id,
            playlist=self._to_domain_playlist(orm.playlist),
            created_time=orm.created_at,
        )

    def _to_orm(self, domain: Session) -> SessionEntity:
        orm = SessionEntity(
            id=domain.id,
            title=domain.title,
            owner_id=domain.owner_id,
            created_at=domain.created_at,
            last_activity_at=self._resolve_last_activity_at(domain),
        )
        orm.messages = [
            self._to_orm_message(
                message=message,
                session_id=domain.id,
                position=index,
            )
            for index, message in enumerate(domain.messages)
        ]
        orm.playlist = self._to_orm_playlist(
            domain_playlist=domain.playlist,
            session_id=domain.id,
        )
        return orm

    async def get_by_id(self, *, session_id: UUID) -> Session:
        session = await self.session.scalar(self._detail_query(session_id=session_id))
        if session is None:
            raise SessionNotFoundError
        return self._to_domain(session)

    async def update(
        self,
        *,
        session_id: UUID,
        title: str | None,
    ) -> Session:
        session = await self.get_by_id(session_id=session_id)
        if title is not None:
            session.title = title
        return await self.save(session=session)

    async def delete(self, *, session_id: UUID) -> None:
        deleted = await self.delete_by_id(session_id)
        if not deleted:
            raise SessionNotFoundError

    async def save(self, *, session: Session) -> Session:
        orm = await self.session.scalar(self._detail_query(session_id=session.id))
        if orm is None:
            orm = SessionEntity(id=session.id)
            self.session.add(orm)

        orm.title = session.title
        orm.owner_id = session.owner_id
        orm.created_at = session.created_at
        orm.last_activity_at = self._resolve_last_activity_at(session)

        session_id = orm.id or session.id
        orm.messages = [
            self._to_orm_message(
                message=message,
                session_id=session_id,
                position=index,
            )
            for index, message in enumerate(session.messages)
        ]
        orm.playlist = self._to_orm_playlist(
            domain_playlist=session.playlist,
            session_id=session_id,
        )

        await self.session.flush()
        return self._to_domain(orm)

    def _detail_query(self, *, session_id: UUID):
        return (
            select(SessionEntity)
            .where(SessionEntity.id == session_id)
            .options(
                selectinload(SessionEntity.messages),
                selectinload(SessionEntity.playlist).selectinload(
                    SessionPlaylistEntity.tracks
                ),
            )
        )

    def _resolve_last_activity_at(self, session: Session) -> datetime:
        if not session.messages:
            return session.created_at

        latest_message_created_at = max(
            message.created_at for message in session.messages
        )
        return max(session.created_at, latest_message_created_at)

    def _to_orm_message(
        self,
        *,
        message: SessionMessage,
        session_id: UUID,
        position: int,
    ) -> SessionMessageEntity:
        return SessionMessageEntity(
            id=message.id,
            session_id=session_id,
            position=position,
            role=message.role.value,
            content=message.content,
            tool_call_group=(
                self._to_orm_tool_call_group(message.tool_call_group)
                if message.tool_call_group is not None
                else None
            ),
            follow_up_group=(
                self._to_orm_follow_up_group(message.follow_up_group)
                if message.follow_up_group is not None
                else None
            ),
            created_at=message.created_at,
        )

    def _to_domain_message(self, orm: SessionMessageEntity) -> SessionMessage:
        tool_call_group = (
            self._to_domain_tool_call_group(orm.tool_call_group)
            if isinstance(orm.tool_call_group, dict)
            else None
        )

        follow_up_group = (
            self._to_domain_follow_up_group(orm.follow_up_group)
            if isinstance(orm.follow_up_group, dict)
            else None
        )

        return SessionMessage(
            id=orm.id,
            role=MessageRole(orm.role),
            content=orm.content,
            tool_call_group=tool_call_group,
            follow_up_group=follow_up_group,
            created_time=orm.created_at,
        )

    def _to_orm_tool_call_group(self, group: ToolCallGroup) -> dict[str, object]:
        return {
            "id": str(group.id),
            "created_at": group.created_at.isoformat(),
            "calls": [self._to_orm_tool_call(call) for call in group.calls],
        }

    def _to_domain_tool_call_group(self, payload: dict[str, object]) -> ToolCallGroup:
        calls_payload = payload.get("calls")
        calls = (
            [
                self._to_domain_tool_call(item)
                for item in calls_payload
                if isinstance(item, dict)
            ]
            if isinstance(calls_payload, list)
            else []
        )

        return ToolCallGroup(
            id=_parse_uuid(payload.get("id")),
            calls=calls,
            created_time=_parse_datetime(payload.get("created_at")),
        )

    def _to_orm_tool_call(self, call: ToolCall) -> dict[str, object]:
        return {
            "id": call.id,
            "function": {
                "name": call.function.name,
                "arguments": call.function.arguments,
            },
            "state": call.state.value,
            "result": call.result,
            "error": call.error,
        }

    def _to_domain_tool_call(self, payload: dict[str, object]) -> ToolCall:
        function_payload = payload.get("function")
        if not isinstance(function_payload, dict):
            function_payload = {}

        arguments = function_payload.get("arguments")
        if not isinstance(arguments, dict):
            arguments = {}

        state_value = payload.get("state", ToolCallState.PENDING.value)
        result = payload.get("result")
        error = payload.get("error")

        return ToolCall(
            id=str(payload.get("id", "")),
            function=ToolFunction(
                name=str(function_payload.get("name", "")),
                arguments=arguments,
            ),
            state=ToolCallState(state_value),
            result=str(result) if isinstance(result, str) else None,
            error=str(error) if isinstance(error, str) else None,
        )

    def _to_orm_follow_up_group(
        self, group: FollowUpQuestionGroup
    ) -> dict[str, object]:
        return {
            "id": str(group.id),
            "created_at": group.created_at.isoformat(),
            "questions": [
                self._to_orm_follow_up_question(question)
                for question in group.questions
            ],
        }

    def _to_domain_follow_up_group(
        self, payload: dict[str, object]
    ) -> FollowUpQuestionGroup:
        questions_payload = payload.get("questions")
        questions = (
            [
                self._to_domain_follow_up_question(item)
                for item in questions_payload
                if isinstance(item, dict)
            ]
            if isinstance(questions_payload, list)
            else []
        )

        return FollowUpQuestionGroup(
            id=_parse_uuid(payload.get("id")),
            questions=questions,
            created_time=_parse_datetime(payload.get("created_at")),
        )

    def _to_orm_follow_up_question(
        self, question: FollowUpQuestion
    ) -> dict[str, object]:
        return {
            "id": str(question.id),
            "created_at": question.created_at.isoformat(),
            "question": question.question,
            "options": [
                {"id": option.id, "label": option.label} for option in question.options
            ],
            "state": question.state.value,
            "answer_text": question.answer_text,
            "answered_option_id": question.answered_option_id,
        }

    def _to_domain_follow_up_question(
        self, payload: dict[str, object]
    ) -> FollowUpQuestion:
        options_payload = payload.get("options")
        options = (
            [
                FollowUpOption(
                    id=str(item.get("id", "")),
                    label=str(item.get("label", "")),
                )
                for item in options_payload
                if isinstance(item, dict)
            ]
            if isinstance(options_payload, list)
            else []
        )

        state_value = payload.get("state", FollowUpQuestionState.PENDING.value)
        answer_text = payload.get("answer_text")
        answered_option_id = payload.get("answered_option_id")

        return FollowUpQuestion(
            id=_parse_uuid(payload.get("id")),
            created_time=_parse_datetime(payload.get("created_at")),
            question=str(payload.get("question", "")),
            options=options,
            state=FollowUpQuestionState(state_value),
            answer_text=str(answer_text) if isinstance(answer_text, str) else None,
            answered_option_id=(
                str(answered_option_id) if isinstance(answered_option_id, str) else None
            ),
        )

    def _to_orm_playlist(
        self,
        *,
        domain_playlist: Playlist | None,
        session_id: UUID,
    ) -> SessionPlaylistEntity | None:
        if domain_playlist is None:
            return None

        orm_playlist = SessionPlaylistEntity(
            id=domain_playlist.id,
            session_id=session_id,
            name=domain_playlist.name,
            created_at=domain_playlist.created_at,
        )
        orm_playlist.tracks = [
            self._to_orm_track(
                track=track,
                playlist_id=domain_playlist.id,
                position=index,
            )
            for index, track in enumerate(domain_playlist.tracks)
        ]
        return orm_playlist

    def _to_domain_playlist(
        self,
        orm_playlist: SessionPlaylistEntity | None,
    ) -> Playlist | None:
        if orm_playlist is None:
            return None

        tracks = sorted(orm_playlist.tracks, key=lambda item: item.position)
        return Playlist(
            id=orm_playlist.id,
            name=orm_playlist.name,
            tracks=[self._to_domain_track(track) for track in tracks],
            created_time=orm_playlist.created_at,
        )

    def _to_orm_track(
        self,
        *,
        track: PlaylistTrack,
        playlist_id: UUID,
        position: int,
    ) -> PlaylistTrackEntity:
        return PlaylistTrackEntity(
            id=track.id,
            playlist_id=playlist_id,
            position=position,
            title=track.title,
            artist=track.artist,
            year=track.year,
            cover_url=track.cover_url,
            created_at=track.created_at,
        )

    def _to_domain_track(self, orm_track: PlaylistTrackEntity) -> PlaylistTrack:
        return PlaylistTrack(
            id=orm_track.id,
            title=orm_track.title,
            artist=orm_track.artist,
            year=orm_track.year,
            cover_url=orm_track.cover_url,
            created_time=orm_track.created_at,
        )


def _parse_uuid(value: object) -> UUID | None:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str) and value:
        try:
            return UUID(value)
        except ValueError:
            return None
    return None


def _parse_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None
    return None
