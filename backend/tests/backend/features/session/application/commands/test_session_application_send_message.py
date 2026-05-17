import asyncio
from collections.abc import AsyncIterator
from typing import cast
from uuid import UUID, uuid4

from llmify import ChatModel, Message, UserMessage

from backend.features.session.application.commands.send_message import (
    SendMessageHandler,
)
from backend.features.session.domain import MessageRole, Session, SessionRepository


class _SessionRepositoryStub(SessionRepository):
    def __init__(self) -> None:
        self.saved_sessions: list[Session] = []

    async def get_by_id(self, session_id: UUID) -> Session:
        raise AssertionError("get_by_id is not used in SendMessageHandler tests")

    async def save(self, *, session: Session) -> Session:
        self.saved_sessions.append(session)
        return session

    async def update(self, session_id: UUID, title: str | None) -> Session:
        raise AssertionError("update is not used in SendMessageHandler tests")

    async def delete(self, session_id: UUID) -> None:
        raise AssertionError("delete is not used in SendMessageHandler tests")


class _ChatModelStub:
    def __init__(self, chunks: list[str]) -> None:
        self._chunks = chunks
        self.contexts: list[list[Message]] = []

    async def stream(self, messages: list[Message]) -> AsyncIterator[str]:
        self.contexts.append(messages)
        for chunk in self._chunks:
            yield chunk


async def _collect_chunks(iterator: AsyncIterator[str]) -> list[str]:
    return [chunk async for chunk in iterator]


class TestSendMessageHandler:
    def test_stream_response_adds_user_message_then_assistant_message(self) -> None:
        session = Session(title="Roadtrip", messages=[], owner_id=uuid4())
        repository = _SessionRepositoryStub()
        llm = _ChatModelStub(chunks=["Hallo", " Welt"])
        handler = SendMessageHandler(
            llm=cast(ChatModel, llm),
            session_repository=repository,
        )

        yielded = asyncio.run(
            _collect_chunks(handler.stream_response(session=session, content="Hi"))
        )

        assert yielded == ["Hallo", " Welt"]
        assert [message.role for message in session.messages] == [
            MessageRole.USER,
            MessageRole.ASSISTANT,
        ]
        assert session.messages[0].content == "Hi"
        assert session.messages[1].content == "Hallo Welt"
        assert len(repository.saved_sessions) == 2
        assert len(llm.contexts) == 1
        assert len(llm.contexts[0]) == 1
        assert isinstance(llm.contexts[0][0], UserMessage)
        assert llm.contexts[0][0].content == "Hi"

    def test_stream_response_does_not_append_duplicate_latest_user_message(
        self,
    ) -> None:
        session = Session(title="Roadtrip", messages=[], owner_id=uuid4())
        session.add_user_message(content="Hi")
        repository = _SessionRepositoryStub()
        llm = _ChatModelStub(chunks=["Antwort"])
        handler = SendMessageHandler(
            llm=cast(ChatModel, llm),
            session_repository=repository,
        )

        yielded = asyncio.run(
            _collect_chunks(handler.stream_response(session=session, content="Hi"))
        )

        assert yielded == ["Antwort"]
        assert [message.role for message in session.messages] == [
            MessageRole.USER,
            MessageRole.ASSISTANT,
        ]
        assert len(repository.saved_sessions) == 1

    def test_stream_response_ignores_empty_chunks_and_skips_blank_completion(
        self,
    ) -> None:
        session = Session(title="Roadtrip", messages=[], owner_id=uuid4())
        repository = _SessionRepositoryStub()
        llm = _ChatModelStub(chunks=["", "   ", "\n"])
        handler = SendMessageHandler(
            llm=cast(ChatModel, llm),
            session_repository=repository,
        )

        yielded = asyncio.run(
            _collect_chunks(handler.stream_response(session=session, content="Hi"))
        )

        assert yielded == ["   ", "\n"]
        assert [message.role for message in session.messages] == [MessageRole.USER]
        assert len(repository.saved_sessions) == 1
