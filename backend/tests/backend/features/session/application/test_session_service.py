import asyncio
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from backend.features.session.application.events import (
    SessionFollowUpAnswered,
    SessionFollowUpGroupCompleted,
    SessionUserMessageAppended,
)
from backend.features.session.application.ports.session_summary_query import (
    SessionSummary,
    SessionSummaryQuery,
)
from backend.features.session.application.ports.title_generator import (
    SessionTitleGenerator,
)
from backend.features.session.application.session_service import SessionService
from backend.features.session.domain import (
    FollowUpOption,
    FollowUpQuestion,
    FollowUpQuestionState,
    Session,
    SessionAccessDeniedError,
    SessionRepository,
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


def _make_service(
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


class TestSessionServiceGetById:
    def test_loads_session_and_allows_owner(self) -> None:
        owner_id = uuid4()
        session = Session(title="Roadtrip", messages=[], owner_id=owner_id)
        repository = _SessionRepositoryStub(session_by_id=session)
        service = _make_service(repository=repository)

        result = asyncio.run(service.get_by_id(session_id=session.id, user_id=owner_id))

        assert result is session

    def test_raises_when_user_does_not_own_session(self) -> None:
        session = Session(title="Roadtrip", messages=[], owner_id=uuid4())
        repository = _SessionRepositoryStub(session_by_id=session)
        service = _make_service(repository=repository)

        with pytest.raises(SessionAccessDeniedError, match="does not have access"):
            asyncio.run(service.get_by_id(session_id=session.id, user_id=uuid4()))


class TestSessionServiceCreate:
    def test_generates_trimmed_limited_title_and_persists_session(self) -> None:
        from backend.features.session.domain import MessageRole

        owner_id = uuid4()
        initial_prompt = "spiele was ruhiges"
        repository = _SessionRepositoryStub()
        generator = _SessionTitleGeneratorStub(generated_title=f"  {'A' * 130}  ")
        service = _make_service(repository=repository, title_generator=generator)

        result = asyncio.run(
            service.create(owner_id=owner_id, initial_prompt=initial_prompt)
        )
        created = result.session

        assert created is repository.created_session
        assert created.title == "A" * 120
        assert created.owner_id == owner_id
        assert len(created.messages) == 1
        assert created.messages[0].role == MessageRole.USER
        assert created.messages[0].content == initial_prompt
        assert generator.received_initial_prompt == initial_prompt

    def test_falls_back_to_new_session_for_blank_generated_title(self) -> None:
        repository = _SessionRepositoryStub()
        generator = _SessionTitleGeneratorStub(generated_title="   ")
        service = _make_service(repository=repository, title_generator=generator)

        result = asyncio.run(service.create(owner_id=uuid4(), initial_prompt="prompt"))

        assert result.session.title == "New Session"


class TestSessionServiceUpdate:
    def test_delegates_to_repository_and_returns_updated_session(self) -> None:
        owner_id = uuid4()
        session = Session(title="Old", messages=[], owner_id=owner_id)
        updated = Session(title="New", messages=[], owner_id=owner_id, id=session.id)
        repository = _SessionRepositoryStub(
            session_by_id=session, updated_session=updated
        )
        service = _make_service(repository=repository)

        result = asyncio.run(
            service.update(session_id=session.id, user_id=owner_id, title="New")
        )

        assert result is updated
        assert repository.received_update_session_id == session.id
        assert repository.received_update_title == "New"

    def test_raises_when_user_does_not_own_session(self) -> None:
        session = Session(title="Old", messages=[], owner_id=uuid4())
        repository = _SessionRepositoryStub(session_by_id=session)
        service = _make_service(repository=repository)

        with pytest.raises(SessionAccessDeniedError, match="does not have access"):
            asyncio.run(
                service.update(session_id=session.id, user_id=uuid4(), title="New")
            )


class TestSessionServiceDelete:
    def test_deletes_session_by_id(self) -> None:
        owner_id = uuid4()
        session = Session(title="Roadtrip", messages=[], owner_id=owner_id)
        repository = _SessionRepositoryStub(session_by_id=session)
        service = _make_service(repository=repository)

        asyncio.run(service.delete(session_id=session.id, user_id=owner_id))

        assert repository.deleted_session_id == session.id

    def test_raises_when_user_does_not_own_session(self) -> None:
        session = Session(title="Roadtrip", messages=[], owner_id=uuid4())
        repository = _SessionRepositoryStub(session_by_id=session)
        service = _make_service(repository=repository)

        with pytest.raises(SessionAccessDeniedError, match="does not have access"):
            asyncio.run(service.delete(session_id=session.id, user_id=uuid4()))


class TestSessionServiceList:
    def test_delegates_to_session_summary_query(self) -> None:
        owner_id = uuid4()
        summaries = [
            SessionSummary(
                id=uuid4(),
                title="Roadtrip",
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                last_activity_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            )
        ]
        query = _SessionSummaryQueryStub(summaries=summaries)
        service = _make_service(summary_query=query)

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
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                last_activity_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            )
        ]
        query = _SessionSummaryQueryStub(summaries=summaries)
        service = _make_service(summary_query=query)

        result = asyncio.run(
            service.search(owner_id=owner_id, query="techno", limit=5, offset=15)
        )

        assert result == summaries
        assert query.received_owner_id == owner_id
        assert query.received_query == "techno"
        assert query.received_limit == 5
        assert query.received_offset == 15


class TestSessionServiceFollowUps:
    def test_send_message_skips_pending_follow_ups_before_appending_message(
        self,
    ) -> None:
        owner_id = uuid4()
        first_question = _make_follow_up_question("Welches Genre?")
        second_question = _make_follow_up_question("Welche Stimmung?")
        session = Session(title="Roadtrip", messages=[], owner_id=owner_id)
        session.add_assistant_message(
            follow_up_questions=[first_question, second_question]
        )
        repository = _SessionRepositoryStub(session_by_id=session)
        service = _make_service(repository=repository)

        events = asyncio.run(
            _collect_events(
                service.send_message(
                    session_id=session.id,
                    user_id=owner_id,
                    content="spiele house",
                )
            )
        )

        assert len(events) == 1
        assert isinstance(events[0], SessionUserMessageAppended)
        assert first_question.state == FollowUpQuestionState.SKIPPED
        assert second_question.state == FollowUpQuestionState.SKIPPED
        assert events[0].message.content == "spiele house"
        assert repository.saved_sessions == [session]

    def test_answer_follow_up_emits_completion_when_group_is_complete(self) -> None:
        owner_id = uuid4()
        question = _make_follow_up_question()
        session = Session(title="Roadtrip", messages=[], owner_id=owner_id)
        session.add_assistant_message(follow_up_questions=[question])
        repository = _SessionRepositoryStub(session_by_id=session)
        service = _make_service(repository=repository)

        events = asyncio.run(
            _collect_events(
                service.answer_follow_up(
                    session_id=session.id,
                    user_id=owner_id,
                    question_id=question.id,
                    option_id="house",
                    text=None,
                )
            )
        )

        assert len(events) == 2
        assert isinstance(events[0], SessionFollowUpAnswered)
        assert isinstance(events[1], SessionFollowUpGroupCompleted)
        assert events[1].group_id == session.messages[-1].follow_up_group.id
        assert question.state == FollowUpQuestionState.ANSWERED
        assert repository.saved_sessions == [session]

    def test_skip_remaining_follow_ups_skips_pending_questions(self) -> None:
        owner_id = uuid4()
        first_question = _make_follow_up_question("Welches Genre?")
        second_question = _make_follow_up_question("Welche Stimmung?")
        third_question = _make_follow_up_question("Welches Tempo?")
        session = Session(title="Roadtrip", messages=[], owner_id=owner_id)
        session.add_assistant_message(
            follow_up_questions=[first_question, second_question, third_question]
        )
        first_question.answer_with_text("house")
        repository = _SessionRepositoryStub(session_by_id=session)
        service = _make_service(repository=repository)

        events = asyncio.run(
            _collect_events(
                service.skip_remaining_follow_ups(
                    session_id=session.id,
                    user_id=owner_id,
                )
            )
        )

        assert len(events) == 1
        assert isinstance(events[0], SessionFollowUpGroupCompleted)
        assert first_question.state == FollowUpQuestionState.ANSWERED
        assert second_question.state == FollowUpQuestionState.SKIPPED
        assert third_question.state == FollowUpQuestionState.SKIPPED
        assert repository.saved_sessions == [session]
