import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, Column
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field

from backend.features.session.domain import (
    Session,
    SessionNotFoundError,
    SessionRepository,
)
from backend.features.session.domain.views import MessageRole, SessionMessage, ToolCall
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


class SqlSessionRepository(Repository[SessionEntity, Session], SessionRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=SessionEntity)

    def _to_domain(self, orm: SessionEntity) -> Session:
        return Session(
            id=orm.id,
            title=orm.title,
            messages=[self._to_domain_message(message) for message in orm.messages],
            owner_id=orm.owner_id,
            created_time=orm.created_at,
        )

    def _to_orm(self, domain: Session) -> SessionEntity:
        return SessionEntity(
            id=domain.id,
            title=domain.title,
            messages=[self._to_orm_message(message) for message in domain.messages],
            owner_id=domain.owner_id,
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
            "tool_call_id": message.tool_call_id,
            "created_at": message.created_at.isoformat(),
            "tool_calls": (
                [self._to_orm_tool_call(tool_call) for tool_call in message.tool_calls]
                if message.tool_calls
                else None
            ),
        }

    def _to_domain_message(self, payload: dict[str, object]) -> SessionMessage:
        tool_calls_payload = payload.get("tool_calls")
        tool_calls: list[ToolCall] | None = None

        if isinstance(tool_calls_payload, list):
            parsed_tool_calls = [
                self._to_domain_tool_call(item)
                for item in tool_calls_payload
                if isinstance(item, dict)
            ]
            if parsed_tool_calls:
                tool_calls = parsed_tool_calls

        created_at = payload.get("created_at")
        created_time = (
            datetime.fromisoformat(created_at) if isinstance(created_at, str) else None
        )

        message_id = payload.get("id")
        message_uuid = UUID(message_id) if isinstance(message_id, str) else None

        return SessionMessage(
            id=message_uuid,
            role=MessageRole(payload["role"]),
            content=str(payload.get("content", "")),
            tool_calls=tool_calls,
            tool_call_id=(
                str(payload["tool_call_id"])
                if payload.get("tool_call_id") is not None
                else None
            ),
            created_time=created_time,
        )

    def _to_orm_tool_call(self, tool_call: ToolCall) -> dict[str, object]:
        return {
            "id": tool_call.id,
            "type": tool_call.type,
            "function": {
                "name": tool_call.function.name,
                "arguments": json.dumps(tool_call.function.arguments),
            },
        }

    def _to_domain_tool_call(self, payload: dict[str, object]) -> ToolCall:
        function_payload = payload.get("function")
        if not isinstance(function_payload, dict):
            function_payload = {}

        arguments = function_payload.get("arguments")
        if not isinstance(arguments, str):
            arguments = json.dumps(arguments if arguments is not None else {})

        return ToolCall.from_dict(
            {
                "id": str(payload.get("id", "")),
                "function": {
                    "name": str(function_payload.get("name", "")),
                    "arguments": arguments,
                },
            }
        )
