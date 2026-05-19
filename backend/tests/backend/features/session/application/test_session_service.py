import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from backend.features.session.application.events import (
    SessionAssistantMessageChunk,
    SessionAssistantMessageCompleted,
    SessionAssistantMessageStarted,
    SessionToolCallResolved,
)
from backend.features.session.application.ports.session_runner import (
    SessionRunner,
    SessionRunnerAssistantMessage,
    SessionRunnerEvent,
)
from backend.features.session.application.ports.session_summary_query import (
    SessionSummary,
    SessionSummaryQuery,
)
from backend.features.session.application.ports.title_generator import (
    SessionTitleGenerator,
)
from backend.features.session.application.conversation_service import (
    FollowUpAnswer,
    SessionConversationService,
)
from backend.features.session.application.session_service import (
    SessionService,
)
from backend.features.session.domain import (
    FollowUpOption,
    FollowUpQuestion,
    FollowUpQuestionState,
    PendingCall,
    Session,
    SessionAccessDeniedError,
    SessionRepository,
    ToolFunction,
    UserMessage,
)


class _SessionRepositoryStub(SessionRepository):
    def __init__(
        self,
        *,
        session_by_id: Session | None = None,
        updated_session: Session | None = None,
    ) -> None:
        self._session_by_id = session_by_id
        self._updated_session = updated_session
        self.saved_sessions: list[Session] = []
        self.created_session: Session | None = None
        self.deleted_session_id: UUID | None = None
        self.received_update_session_id: UUID | None = None
        self.received_update_title: str | None = None

    async def get_by_id(self, session_id: UUID) -> Session:
        assert self._session_by_id is not None
        return self._session_by_id

    async def create(self, *, session: Session) -> Session:
        self.created_session = session
        return session

    async def save(self, *, session: Session) -> Session:
        self.saved_sessions.append(session)
        return session

    async def update(self, session_id: UUID, title: str | None) -> Session:
        self.received_update_session_id = session_id
        self.received_update_title = title
        assert self._updated_session is not None
        return self._updated_session

    async def delete(self, session_id: UUID) -> None:
        self.deleted_session_id = session_id


class _SessionSummaryQueryStub(SessionSummaryQuery):
    def __init__(self, summaries: list[SessionSummary]) -> None:
        self._summaries = summaries
        self.received_owner_id: UUID | None = None
        self.received_query: str | None = None
        self.received_limit: int | None = None
        self.received_offset: int | None = None

    async def list_for_owner(
        self,
        *,
        owner_id: UUID,
        limit: int,
        offset: int,
    ) -> list[SessionSummary]:
        self.received_owner_id = owner_id
        self.received_limit = limit
        self.received_offset = offset
        return self._summaries

    async def search_for_owner(
        self,
        *,
        owner_id: UUID,
        query: str,
        limit: int,
        offset: int,
    ) -> list[SessionSummary]:
        self.received_owner_id = owner_id
        self.received_query = query
        self.received_limit = limit
        self.received_offset = offset
        return self._summaries


class _SessionTitleGeneratorStub(SessionTitleGenerator):
    def __init__(self, generated_title: str) -> None:
        self._generated_title = generated_title
        self.received_initial_prompt: str | None = None

    async def generate(self, initial_prompt: str) -> str:
        self.received_initial_prompt = initial_prompt
        return self._generated_title


class _SessionRunnerStub(SessionRunner):
    def __init__(self, chunks: list[str] | None = None) -> None:
        self._chunks = chunks or ["Hello", " world"]

    async def run(self, *, session: Session) -> AsyncIterator[SessionRunnerEvent]:
        yield SessionRunnerAssistantMessage(content="".join(self._chunks))


def _make_management_service(
    *,
    repository: _SessionRepositoryStub | None = None,
    summary_query: _SessionSummaryQueryStub | None = None,
    title_generator: _SessionTitleGeneratorStub | None = None,
) -> SessionService:
    return SessionService(
        session_repository=repository or _SessionRepositoryStub(),
        session_summary_query=summary_query or _SessionSummaryQueryStub(summaries=[]),
        title_generator=title_generator
        or _SessionTitleGeneratorStub(generated_title=""),
    )


def _make_conversation_service(
    *,
    repository: _SessionRepositoryStub | None = None,
    runner: _SessionRunnerStub | None = None,
) -> SessionConversationService:
    return SessionConversationService(
        session_repository=repository or _SessionRepositoryStub(),
        runner=runner or _SessionRunnerStub(),
    )


async def _collect_events(iterator):
    return [event async for event in iterator]


def _make_follow_up_question(question: str = "Welches Genre?") -> FollowUpQuestion:
    return FollowUpQuestion(
        question=question,
        options=[
            FollowUpOption(id="house", label="House"),
            FollowUpOption(id="techno", label="Techno"),
        ],
    )


def _add_pending_follow_up_tool_call(session: Session) -> None:
    session.add_tool_call(
        PendingCall(
            id="call-follow-up",
            function=ToolFunction(
                name="ask_follow_up",
                arguments={"questions": []},
            ),
        )
    )


class TestSessionServiceGetById:
    def test_loads_session_and_allows_owner(self) -> None:
        owner_id = uuid4()
        session = Session(title="Roadtrip", entries=[], owner_id=owner_id)
        repository = _SessionRepositoryStub(session_by_id=session)
        service = _make_management_service(repository=repository)

        result = asyncio.run(service.get_by_id(session_id=session.id, user_id=owner_id))

        assert result is session

    def test_raises_when_user_does_not_own_session(self) -> None:
        session = Session(title="Roadtrip", entries=[], owner_id=uuid4())
        repository = _SessionRepositoryStub(session_by_id=session)
        service = _make_management_service(repository=repository)

        with pytest.raises(SessionAccessDeniedError, match="does not have access"):
            asyncio.run(service.get_by_id(session_id=session.id, user_id=uuid4()))


class TestSessionServiceCreate:
    def test_generates_trimmed_limited_title_and_persists_session(self) -> None:
        owner_id = uuid4()
        initial_prompt = "spiele was ruhiges"
        repository = _SessionRepositoryStub()
        generator = _SessionTitleGeneratorStub(generated_title=f"  {'A' * 130}  ")
        service = _make_management_service(
            repository=repository,
            title_generator=generator,
        )

        created = asyncio.run(
            service.create(owner_id=owner_id, initial_prompt=initial_prompt)
        )

        assert created is repository.created_session
        assert created.title == "A" * 120
        assert created.owner_id == owner_id
        assert len(created.entries) == 1
        assert isinstance(created.entries[0], UserMessage)
        assert created.entries[0].content == initial_prompt
        assert generator.received_initial_prompt == initial_prompt

    def test_falls_back_to_new_session_for_blank_generated_title(self) -> None:
        repository = _SessionRepositoryStub()
        generator = _SessionTitleGeneratorStub(generated_title="   ")
        service = _make_management_service(
            repository=repository,
            title_generator=generator,
        )

        session = asyncio.run(service.create(owner_id=uuid4(), initial_prompt="prompt"))

        assert session.title == "New Session"


class TestSessionServiceUpdate:
    def test_delegates_to_repository_and_returns_updated_session(self) -> None:
        owner_id = uuid4()
        session = Session(title="Old", entries=[], owner_id=owner_id)
        updated = Session(title="New", entries=[], owner_id=owner_id, id=session.id)
        repository = _SessionRepositoryStub(
            session_by_id=session, updated_session=updated
        )
        service = _make_management_service(repository=repository)

        result = asyncio.run(
            service.update(session_id=session.id, user_id=owner_id, title="New")
        )

        assert result is updated
        assert repository.received_update_session_id == session.id
        assert repository.received_update_title == "New"

    def test_raises_when_user_does_not_own_session(self) -> None:
        session = Session(title="Old", entries=[], owner_id=uuid4())
        repository = _SessionRepositoryStub(session_by_id=session)
        service = _make_management_service(repository=repository)

        with pytest.raises(SessionAccessDeniedError, match="does not have access"):
            asyncio.run(
                service.update(session_id=session.id, user_id=uuid4(), title="New")
            )


class TestSessionServiceDelete:
    def test_deletes_session_by_id(self) -> None:
        owner_id = uuid4()
        session = Session(title="Roadtrip", entries=[], owner_id=owner_id)
        repository = _SessionRepositoryStub(session_by_id=session)
        service = _make_management_service(repository=repository)

        asyncio.run(service.delete(session_id=session.id, user_id=owner_id))

        assert repository.deleted_session_id == session.id

    def test_raises_when_user_does_not_own_session(self) -> None:
        session = Session(title="Roadtrip", entries=[], owner_id=uuid4())
        repository = _SessionRepositoryStub(session_by_id=session)
        service = _make_management_service(repository=repository)

        with pytest.raises(SessionAccessDeniedError, match="does not have access"):
            asyncio.run(service.delete(session_id=session.id, user_id=uuid4()))


class TestSessionServiceStar:
    def test_marks_session_as_starred_and_persists(self) -> None:
        owner_id = uuid4()
        session = Session(title="Roadtrip", entries=[], owner_id=owner_id)
        repository = _SessionRepositoryStub(session_by_id=session)
        service = _make_management_service(repository=repository)

        result = asyncio.run(service.star(session_id=session.id, user_id=owner_id))

        assert result is session
        assert result.is_starred is True
        assert repository.saved_sessions == [session]

    def test_raises_when_user_does_not_own_session(self) -> None:
        session = Session(title="Roadtrip", entries=[], owner_id=uuid4())
        repository = _SessionRepositoryStub(session_by_id=session)
        service = _make_management_service(repository=repository)

        with pytest.raises(SessionAccessDeniedError, match="does not have access"):
            asyncio.run(service.star(session_id=session.id, user_id=uuid4()))


class TestSessionServiceUnstar:
    def test_marks_session_as_not_starred_and_persists(self) -> None:
        owner_id = uuid4()
        session = Session(title="Roadtrip", entries=[], owner_id=owner_id)
        session.star()
        repository = _SessionRepositoryStub(session_by_id=session)
        service = _make_management_service(repository=repository)

        result = asyncio.run(service.unstar(session_id=session.id, user_id=owner_id))

        assert result is session
        assert result.is_starred is False
        assert repository.saved_sessions == [session]

    def test_raises_when_user_does_not_own_session(self) -> None:
        session = Session(title="Roadtrip", entries=[], owner_id=uuid4())
        repository = _SessionRepositoryStub(session_by_id=session)
        service = _make_management_service(repository=repository)

        with pytest.raises(SessionAccessDeniedError, match="does not have access"):
            asyncio.run(service.unstar(session_id=session.id, user_id=uuid4()))


class TestSessionServiceList:
    def test_delegates_to_session_summary_query(self) -> None:
        owner_id = uuid4()
        summaries = [
            SessionSummary(
                id=uuid4(),
                title="Roadtrip",
                is_starred=False,
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                last_activity_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            )
        ]
        query = _SessionSummaryQueryStub(summaries=summaries)
        service = _make_management_service(summary_query=query)

        result = asyncio.run(service.list(owner_id=owner_id, limit=10, offset=20))

        assert result == summaries
        assert query.received_owner_id == owner_id
        assert query.received_limit == 10
        assert query.received_offset == 20


class TestSessionServiceSearch:
    def test_delegates_to_session_summary_query(self) -> None:
        owner_id = uuid4()
        summaries = [
            SessionSummary(
                id=uuid4(),
                title="Techno Mix",
                is_starred=True,
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                last_activity_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            )
        ]
        query = _SessionSummaryQueryStub(summaries=summaries)
        service = _make_management_service(summary_query=query)

        result = asyncio.run(
            service.search(owner_id=owner_id, query="techno", limit=5, offset=15)
        )

        assert result == summaries
        assert query.received_owner_id == owner_id
        assert query.received_query == "techno"
        assert query.received_limit == 5
        assert query.received_offset == 15


class TestSessionServiceSendMessage:
    def test_skips_pending_follow_ups_then_streams_llm(self) -> None:
        owner_id = uuid4()
        first_question = _make_follow_up_question("Welches Genre?")
        second_question = _make_follow_up_question("Welche Stimmung?")
        session = Session(title="Roadtrip", entries=[], owner_id=owner_id)
        _add_pending_follow_up_tool_call(session)
        session.add_follow_up_questions([first_question, second_question])
        repository = _SessionRepositoryStub(session_by_id=session)
        runner = _SessionRunnerStub(chunks=["Hi"])
        service = _make_conversation_service(repository=repository, runner=runner)

        events = asyncio.run(
            _collect_events(
                service.send_message(
                    session_id=session.id,
                    user_id=owner_id,
                    content="spiele house",
                )
            )
        )

        assert first_question.state == FollowUpQuestionState.SKIPPED
        assert second_question.state == FollowUpQuestionState.SKIPPED
        assert any(isinstance(event, SessionToolCallResolved) for event in events)
        assistant_started_index = next(
            index
            for index, event in enumerate(events)
            if isinstance(event, SessionAssistantMessageStarted)
        )
        assert isinstance(
            events[assistant_started_index + 1], SessionAssistantMessageChunk
        )
        assert events[assistant_started_index + 1].chunk == "Hi"
        assert isinstance(events[-1], SessionAssistantMessageCompleted)


class TestSessionServiceFollowUps:
    def test_answer_follow_ups_with_option_and_streams_llm(self) -> None:
        owner_id = uuid4()
        question = _make_follow_up_question()
        session = Session(title="Roadtrip", entries=[], owner_id=owner_id)
        _add_pending_follow_up_tool_call(session)
        session.add_follow_up_questions([question])
        repository = _SessionRepositoryStub(session_by_id=session)
        runner = _SessionRunnerStub(chunks=["chunk1", "chunk2"])
        service = _make_conversation_service(repository=repository, runner=runner)

        events = asyncio.run(
            _collect_events(
                service.answer_follow_ups(
                    session_id=session.id,
                    user_id=owner_id,
                    answers=[
                        FollowUpAnswer(
                            question_id=question.id,
                            option_id="house",
                            text=None,
                        )
                    ],
                )
            )
        )

        assert question.state == FollowUpQuestionState.ANSWERED
        assert isinstance(events[0], SessionToolCallResolved)
        assert isinstance(events[2], SessionAssistantMessageStarted)
        assert isinstance(events[3], SessionAssistantMessageChunk)
        assert events[3].chunk == "chunk1chunk2"
        assert isinstance(events[4], SessionAssistantMessageCompleted)
        assert len(repository.saved_sessions) == 3

    def test_answer_follow_ups_with_text_and_streams_llm(self) -> None:
        owner_id = uuid4()
        question = _make_follow_up_question()
        session = Session(title="Roadtrip", entries=[], owner_id=owner_id)
        _add_pending_follow_up_tool_call(session)
        session.add_follow_up_questions([question])
        repository = _SessionRepositoryStub(session_by_id=session)
        service = _make_conversation_service(repository=repository)

        events = asyncio.run(
            _collect_events(
                service.answer_follow_ups(
                    session_id=session.id,
                    user_id=owner_id,
                    answers=[
                        FollowUpAnswer(
                            question_id=question.id,
                            option_id=None,
                            text="etwas ruhiges",
                        )
                    ],
                )
            )
        )

        assert question.state == FollowUpQuestionState.ANSWERED
        assert isinstance(events[0], SessionToolCallResolved)
        assert isinstance(events[-1], SessionAssistantMessageCompleted)

    def test_skip_remaining_follow_ups_skips_pending_questions_and_streams_llm(
        self,
    ) -> None:
        owner_id = uuid4()
        first_question = _make_follow_up_question("Welches Genre?")
        second_question = _make_follow_up_question("Welche Stimmung?")
        third_question = _make_follow_up_question("Welches Tempo?")
        session = Session(title="Roadtrip", entries=[], owner_id=owner_id)
        _add_pending_follow_up_tool_call(session)
        session.add_follow_up_questions(
            [first_question, second_question, third_question]
        )
        first_question.answer_with_text("house")
        repository = _SessionRepositoryStub(session_by_id=session)
        service = _make_conversation_service(repository=repository)

        events = asyncio.run(
            _collect_events(
                service.skip_remaining_follow_ups(
                    session_id=session.id,
                    user_id=owner_id,
                )
            )
        )

        assert first_question.state == FollowUpQuestionState.ANSWERED
        assert second_question.state == FollowUpQuestionState.SKIPPED
        assert third_question.state == FollowUpQuestionState.SKIPPED
        assert isinstance(events[0], SessionToolCallResolved)
        assert isinstance(events[-1], SessionAssistantMessageCompleted)
