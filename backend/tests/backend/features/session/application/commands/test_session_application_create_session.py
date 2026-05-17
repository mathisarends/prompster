import asyncio
from uuid import UUID, uuid4

from backend.features.session.application.commands.create_session import (
    CreateSessionHandler,
)
from backend.features.session.application.events import SessionTitleGenerated
from backend.features.session.application.ports.title_generator import (
    SessionTitleGenerator,
)
from backend.features.session.domain import MessageRole, Session, SessionRepository


class _SessionRepositoryStub(SessionRepository):
    def __init__(self) -> None:
        self.created_session: Session | None = None

    async def get_by_id(self, session_id: UUID) -> Session:
        raise AssertionError("get_by_id is not used in CreateSessionHandler tests")

    async def save(self, *, session: Session) -> Session:
        self.created_session = session
        return session

    async def update(self, session_id: UUID, title: str | None) -> Session:
        raise AssertionError("update is not used in CreateSessionHandler tests")

    async def delete(self, session_id: UUID) -> None:
        raise AssertionError("delete is not used in CreateSessionHandler tests")


class _SessionTitleGeneratorStub(SessionTitleGenerator):
    def __init__(self, generated_title: str) -> None:
        self._generated_title = generated_title
        self.received_initial_prompt: str | None = None

    async def generate(self, initial_prompt: str) -> str:
        self.received_initial_prompt = initial_prompt
        return self._generated_title


class TestCreateSessionHandler:
    def test_handle_generates_trimmed_limited_title_and_persists_session(self) -> None:
        owner_id = uuid4()
        initial_prompt = "spiele was ruhiges"
        repository = _SessionRepositoryStub()
        generator = _SessionTitleGeneratorStub(generated_title=f"  {'A' * 130}  ")
        handler = CreateSessionHandler(
            session_repository=repository, title_generator=generator
        )

        result = asyncio.run(
            handler.handle(owner_id=owner_id, initial_prompt=initial_prompt)
        )
        created = result.session

        assert created is repository.created_session
        assert created.title == "A" * 120
        assert created.owner_id == owner_id
        assert len(created.messages) == 1
        assert created.messages[0].role == MessageRole.USER
        assert created.messages[0].content == initial_prompt
        assert generator.received_initial_prompt == initial_prompt
        assert result.events == (
            SessionTitleGenerated(session_id=created.id, title="A" * 120),
        )

    def test_handle_falls_back_to_new_session_for_blank_generated_title(self) -> None:
        repository = _SessionRepositoryStub()
        generator = _SessionTitleGeneratorStub(generated_title="   ")
        handler = CreateSessionHandler(
            session_repository=repository, title_generator=generator
        )

        result = asyncio.run(handler.handle(owner_id=uuid4(), initial_prompt="prompt"))

        assert result.session.title == "New Session"
        assert result.events == (
            SessionTitleGenerated(
                session_id=result.session.id,
                title="New Session",
            ),
        )
