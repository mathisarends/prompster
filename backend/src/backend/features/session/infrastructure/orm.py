from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, Column
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field

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
from backend.infrastructure.database.orm import DatabaseEntity
from backend.infrastructure.database.repository import Repository


class SessionEntity(DatabaseEntity, table=True):
    __tablename__ = "sessions"

    title: str
    owner_id: UUID = Field(index=True)
    messages: list[dict[str, object]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    playlist: dict[str, object] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )


class SqlSessionRepository(Repository[SessionEntity, Session], SessionRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=SessionEntity)

    def _to_domain(self, orm: SessionEntity) -> Session:
        return Session(
            id=orm.id,
            title=orm.title,
            messages=[self._to_domain_message(message) for message in orm.messages],
            owner_id=orm.owner_id,
            playlist=self._to_domain_playlist(orm.playlist),
            created_time=orm.created_at,
        )

    def _to_orm(self, domain: Session) -> SessionEntity:
        return SessionEntity(
            id=domain.id,
            title=domain.title,
            messages=[self._to_orm_message(message) for message in domain.messages],
            owner_id=domain.owner_id,
            playlist=self._to_orm_playlist(domain.playlist),
            created_at=domain.created_at,
        )

    async def get_by_id(self, *, session_id: UUID) -> Session:
        session = await self.find_by_id(session_id)
        if session is None:
            raise SessionNotFoundError
        return session

    async def create(self, *, session: Session) -> Session:
        return await self.save(session)

    async def update(
        self,
        *,
        session_id: UUID,
        title: str | None,
    ) -> Session:
        session = await self.get_by_id(session_id=session_id)
        if title is not None:
            session.title = title
        return await self.save(session)

    async def delete(self, *, session_id: UUID) -> None:
        deleted = await self.delete_by_id(session_id)
        if not deleted:
            raise SessionNotFoundError

    def _to_orm_message(self, message: SessionMessage) -> dict[str, object]:
        return {
            "id": str(message.id),
            "role": message.role.value,
            "content": message.content,
            "created_at": message.created_at.isoformat(),
            "tool_call_group": (
                self._to_orm_tool_call_group(message.tool_call_group)
                if message.tool_call_group is not None
                else None
            ),
            "follow_up_group": (
                self._to_orm_follow_up_group(message.follow_up_group)
                if message.follow_up_group is not None
                else None
            ),
        }

    def _to_domain_message(self, payload: dict[str, object]) -> SessionMessage:
        tool_call_payload = payload.get("tool_call_group")
        tool_call_group = (
            self._to_domain_tool_call_group(tool_call_payload)
            if isinstance(tool_call_payload, dict)
            else None
        )

        follow_up_payload = payload.get("follow_up_group")
        follow_up_group = (
            self._to_domain_follow_up_group(follow_up_payload)
            if isinstance(follow_up_payload, dict)
            else None
        )

        return SessionMessage(
            id=_parse_uuid(payload.get("id")),
            role=MessageRole(payload["role"]),
            content=str(payload.get("content", "")),
            tool_call_group=tool_call_group,
            follow_up_group=follow_up_group,
            created_time=_parse_datetime(payload.get("created_at")),
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

    def _to_orm_playlist(self, playlist: Playlist | None) -> dict[str, object] | None:
        if playlist is None:
            return None
        return {
            "id": str(playlist.id),
            "name": playlist.name,
            "created_at": playlist.created_at.isoformat(),
            "tracks": [self._to_orm_track(track) for track in playlist.tracks],
        }

    def _to_domain_playlist(self, payload: dict[str, object] | None) -> Playlist | None:
        if not payload:
            return None

        tracks_payload = payload.get("tracks")
        tracks = (
            [
                self._to_domain_track(item)
                for item in tracks_payload
                if isinstance(item, dict)
            ]
            if isinstance(tracks_payload, list)
            else []
        )

        name = payload.get("name")

        return Playlist(
            id=_parse_uuid(payload.get("id")),
            name=str(name) if isinstance(name, str) else None,
            tracks=tracks,
            created_time=_parse_datetime(payload.get("created_at")),
        )

    def _to_orm_track(self, track: PlaylistTrack) -> dict[str, object]:
        return {
            "id": str(track.id),
            "title": track.title,
            "artist": track.artist,
            "year": track.year,
            "cover_url": track.cover_url,
            "created_at": track.created_at.isoformat(),
        }

    def _to_domain_track(self, payload: dict[str, object]) -> PlaylistTrack:
        year = payload.get("year")

        return PlaylistTrack(
            id=_parse_uuid(payload.get("id")),
            title=str(payload.get("title", "")),
            artist=str(payload.get("artist", "")),
            year=int(year)
            if isinstance(year, (int, str)) and str(year).isdigit()
            else None,
            cover_url=(
                str(payload["cover_url"])
                if payload.get("cover_url") is not None
                else None
            ),
            created_time=_parse_datetime(payload.get("created_at")),
        )


def _parse_uuid(value: object) -> UUID | None:
    return UUID(value) if isinstance(value, str) else None


def _parse_datetime(value: object) -> datetime | None:
    return datetime.fromisoformat(value) if isinstance(value, str) else None
