import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from backend.features.session.application.events import (
    SessionAssistantMessageChunk,
    SessionAssistantMessageCompleted,
    SessionAssistantMessageStarted,
    SessionPlaylistSet,
    SessionPlaylistTrackAdded,
    SessionPlaylistTrackRemoved,
    SessionPlaylistTrackReplaced,
    SessionToolCallSequenceAdded,
    SessionToolCallResolved,
)
from backend.features.session.application.ports.session_runner import (
    SessionRunner,
    SessionRunnerAssistantMessage,
    SessionRunnerAssistantMessageChunk,
    SessionRunnerEvent,
    SessionRunnerPlaylistTrackReplacement,
    SessionRunnerPlaylistTracksAdded,
    SessionRunnerPlaylistTracksRemoved,
    SessionRunnerPlaylistTracksReplaced,
    SessionRunnerPlaylistUpdated,
    SessionRunnerToolCallCompleted,
    SessionRunnerToolCallStarted,
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
    CompletedCall,
    FollowUpOption,
    FollowUpQuestion,
    FollowUpQuestionState,
    PendingCall,
    Playlist,
    PlaylistTrack,
    Session,
    SessionAccessDeniedError,
    SessionRepository,
    ToolCallSequence,
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
    def __init__(
        self,
        chunks: list[str] | None = None,
        events: list[SessionRunnerEvent] | None = None,
    ) -> None:
        self._chunks = chunks or ["Hello", " world"]
        self._events = events

    async def run(self, *, session: Session) -> AsyncIterator[SessionRunnerEvent]:
        if self._events is not None:
            for event in self._events:
                yield event
            return

        for chunk in self._chunks:
            yield SessionRunnerAssistantMessageChunk(chunk=chunk)
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
        assert len(created.entries) == 0
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


class TestSessionServicePlaylistTrackLocks:
    def test_locks_playlist_track_and_persists(self) -> None:
        owner_id = uuid4()
        session = Session(title="Roadtrip", entries=[], owner_id=owner_id)
        track = session.add_track(title="Starlight", artist="Muse")
        repository = _SessionRepositoryStub(session_by_id=session)
        service = _make_management_service(repository=repository)

        result = asyncio.run(
            service.lock_playlist_track(
                session_id=session.id,
                user_id=owner_id,
                track_id=track.id,
            )
        )

        assert result is track
        assert track.is_locked is True
        assert repository.saved_sessions == [session]

    def test_unlocks_playlist_track_and_persists(self) -> None:
        owner_id = uuid4()
        session = Session(title="Roadtrip", entries=[], owner_id=owner_id)
        track = session.add_track(title="Starlight", artist="Muse", is_locked=True)
        repository = _SessionRepositoryStub(session_by_id=session)
        service = _make_management_service(repository=repository)

        result = asyncio.run(
            service.unlock_playlist_track(
                session_id=session.id,
                user_id=owner_id,
                track_id=track.id,
            )
        )

        assert result is track
        assert track.is_locked is False
        assert repository.saved_sessions == [session]


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
    def test_persists_user_message_and_streams_llm(self) -> None:
        owner_id = uuid4()
        prompt = "spiele rihanna hits"
        session = Session(title="Rihanna Deck", entries=[], owner_id=owner_id)
        repository = _SessionRepositoryStub(session_by_id=session)
        runner = _SessionRunnerStub(chunks=["Hi"])
        service = _make_conversation_service(repository=repository, runner=runner)

        events = asyncio.run(
            _collect_events(
                service.send_message(
                    session_id=session.id,
                    user_id=owner_id,
                    content=prompt,
                )
            )
        )

        user_messages = [
            entry for entry in session.entries if isinstance(entry, UserMessage)
        ]
        assert len(user_messages) == 1
        assert user_messages[0].content == prompt
        assert any(
            isinstance(event, SessionAssistantMessageStarted) for event in events
        )
        assert isinstance(events[-1], SessionAssistantMessageCompleted)

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

    def test_batches_consecutive_tool_calls_into_one_sequence(self) -> None:
        owner_id = uuid4()
        session = Session(title="Roadtrip", entries=[], owner_id=owner_id)
        first_call = PendingCall(
            id="call-1",
            function=ToolFunction(name="search_tracks", arguments={"query": "70s"}),
        )
        second_call = PendingCall(
            id="call-2",
            function=ToolFunction(name="search_tracks", arguments={"query": "80s"}),
        )
        runner = _SessionRunnerStub(
            events=[
                SessionRunnerToolCallStarted(call=first_call),
                SessionRunnerToolCallCompleted(
                    tool_call_id="call-1",
                    result="result-1",
                ),
                SessionRunnerToolCallStarted(call=second_call),
                SessionRunnerToolCallCompleted(
                    tool_call_id="call-2",
                    result="result-2",
                ),
            ]
        )
        repository = _SessionRepositoryStub(session_by_id=session)
        service = _make_conversation_service(repository=repository, runner=runner)

        events = asyncio.run(
            _collect_events(
                service.send_message(
                    session_id=session.id,
                    user_id=owner_id,
                    content="baue ein decades deck",
                )
            )
        )

        sequences = [
            entry for entry in session.entries if isinstance(entry, ToolCallSequence)
        ]
        assert len(sequences) == 1
        assert [call.id for call in sequences[0].calls] == ["call-1", "call-2"]
        assert all(isinstance(call, CompletedCall) for call in sequences[0].calls)
        sequence_added_events = [
            event for event in events if isinstance(event, SessionToolCallSequenceAdded)
        ]
        assert len(sequence_added_events) == 2
        assert {event.sequence.id for event in sequence_added_events} == {
            sequences[0].id
        }
        resolved_events = [
            event for event in events if isinstance(event, SessionToolCallResolved)
        ]
        assert [event.sequence_id for event in resolved_events] == [
            sequences[0].id,
            sequences[0].id,
        ]

    def test_emits_playlist_set_for_initial_runner_playlist(self) -> None:
        owner_id = uuid4()
        playlist_id = uuid4()
        track = PlaylistTrack(id=uuid4(), title="Take On Me", artist="a-ha")
        session = Session(title="Roadtrip", entries=[], owner_id=owner_id)
        runner = _SessionRunnerStub(
            events=[
                SessionRunnerPlaylistUpdated(
                    playlist=Playlist(id=playlist_id, name="80er Party", tracks=[track])
                )
            ]
        )
        repository = _SessionRepositoryStub(session_by_id=session)
        service = _make_conversation_service(repository=repository, runner=runner)

        events = asyncio.run(
            _collect_events(
                service.send_message(
                    session_id=session.id,
                    user_id=owner_id,
                    content="baue ein 80er deck",
                )
            )
        )

        playlist_event = next(
            event for event in events if isinstance(event, SessionPlaylistSet)
        )
        assert playlist_event.playlist.id == playlist_id
        assert playlist_event.playlist.name == "80er Party"
        assert playlist_event.playlist.tracks == [track]
        assert session.playlist is not None
        assert session.playlist.id == playlist_id

    def test_emits_playlist_track_diffs_for_runner_playlist_mutations(self) -> None:
        owner_id = uuid4()
        playlist_id = uuid4()
        removed_track = PlaylistTrack(
            id=uuid4(),
            title="Take On Me",
            artist="a-ha",
        )
        added_track = PlaylistTrack(
            id=uuid4(),
            title="Billie Jean",
            artist="Michael Jackson",
        )
        replacement_track = PlaylistTrack(
            id=uuid4(),
            title="Africa",
            artist="Toto",
        )
        session = Session(
            title="Roadtrip",
            entries=[],
            owner_id=owner_id,
            playlist=Playlist(id=playlist_id, tracks=[removed_track]),
        )
        runner = _SessionRunnerStub(
            events=[
                SessionRunnerPlaylistTracksAdded(
                    playlist_id=playlist_id,
                    tracks=[added_track],
                ),
                SessionRunnerPlaylistTracksReplaced(
                    playlist_id=playlist_id,
                    replacements=[
                        SessionRunnerPlaylistTrackReplacement(
                            track_id=added_track.id,
                            track=replacement_track,
                        )
                    ],
                ),
                SessionRunnerPlaylistTracksRemoved(
                    playlist_id=playlist_id,
                    track_ids=[removed_track.id],
                ),
            ]
        )
        repository = _SessionRepositoryStub(session_by_id=session)
        service = _make_conversation_service(repository=repository, runner=runner)

        events = asyncio.run(
            _collect_events(
                service.send_message(
                    session_id=session.id,
                    user_id=owner_id,
                    content="aendere die playlist",
                )
            )
        )

        assert any(
            isinstance(event, SessionPlaylistTrackAdded) and event.track is added_track
            for event in events
        )
        assert any(
            isinstance(event, SessionPlaylistTrackReplaced)
            and event.track_id == added_track.id
            and event.track is replacement_track
            for event in events
        )
        assert any(
            isinstance(event, SessionPlaylistTrackRemoved)
            and event.track_id == removed_track.id
            for event in events
        )
        assert session.playlist is not None
        assert session.playlist.tracks == [replacement_track]


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
        assert events[3].chunk == "chunk1"
        assert isinstance(events[4], SessionAssistantMessageChunk)
        assert events[4].chunk == "chunk2"
        assert isinstance(events[5], SessionAssistantMessageCompleted)
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
