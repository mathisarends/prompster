import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from backend.features.session.application.events import (
    SessionAssistantMessageChunk,
    SessionAssistantMessageCancelled,
    SessionAssistantMessageCompleted,
    SessionAssistantMessageStarted,
    SessionOnboardingQuestionAsked,
    SessionPlaylistSet,
    SessionPlaylistTrackAdded,
    SessionPlaylistTrackRemoved,
    SessionPlaylistTrackReplaced,
    SessionSuspendedForInput,
    SessionTitleGenerated,
    SessionToolCallSequenceAdded,
    SessionToolCallResolved,
    SuspensionKind,
)
from backend.features.session.application.ports.session_runner import (
    SessionRunner,
    SessionRunnerAssistantMessage,
    SessionRunnerAssistantMessageChunk,
    SessionRunnerCancelled,
    SessionRunnerEvent,
    SessionRunnerPlaylistTrackReplacement,
    SessionRunnerPlaylistTracksAdded,
    SessionRunnerPlaylistTracksRemoved,
    SessionRunnerPlaylistTracksReplaced,
    SessionRunnerPlaylistUpdated,
    SessionRunnerQuestionAsked,
    SessionRunnerSuspendedForInput,
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
    SessionConversationService,
)
from backend.features.session.application.session_service import (
    SessionService,
)
from backend.features.session.domain import (
    AssistantMessage,
    CompletedCall,
    DECIDE_FOR_ME_OPTION,
    InvalidSessionPhaseTransitionError,
    PendingCall,
    Phase,
    Playlist,
    PlaylistTrack,
    Session,
    SessionAccessDeniedError,
    SessionRepository,
    ToolCallSequence,
    ToolFunction,
    UserMessage,
)
from backend.features.user.domain import UserMessageQuotaExceededError


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
    def __init__(
        self,
        generated_title: str = "",
        *,
        error: Exception | None = None,
    ) -> None:
        self._generated_title = generated_title
        self._error = error
        self.received_initial_prompt: str | None = None
        self.call_count = 0

    async def generate(self, initial_prompt: str) -> str:
        self.received_initial_prompt = initial_prompt
        self.call_count += 1
        if self._error is not None:
            raise self._error
        return self._generated_title


class _SessionRunnerStub(SessionRunner):
    def __init__(
        self,
        chunks: list[str] | None = None,
        events: list[SessionRunnerEvent] | None = None,
    ) -> None:
        self._chunks = chunks or ["Hello", " world"]
        self._events = events
        self.stopped_session_ids: list[UUID] = []

    async def run(self, *, session: Session) -> AsyncIterator[SessionRunnerEvent]:
        if self._events is not None:
            for event in self._events:
                yield event
            return

        for chunk in self._chunks:
            yield SessionRunnerAssistantMessageChunk(chunk=chunk)
        yield SessionRunnerAssistantMessage(content="".join(self._chunks))

    async def stop(self, *, session_id: UUID) -> bool:
        self.stopped_session_ids.append(session_id)
        return True


class _UserMessageQuotaServiceStub:
    def __init__(self, *, error: Exception | None = None) -> None:
        self._error = error
        self.consumed_user_ids: list[UUID] = []

    async def consume(self, *, user_id: UUID) -> None:
        if self._error is not None:
            raise self._error
        self.consumed_user_ids.append(user_id)


def _make_management_service(
    *,
    repository: _SessionRepositoryStub | None = None,
    summary_query: _SessionSummaryQueryStub | None = None,
) -> SessionService:
    return SessionService(
        session_repository=repository or _SessionRepositoryStub(),
        session_summary_query=summary_query or _SessionSummaryQueryStub(summaries=[]),
    )


def _make_conversation_service(
    *,
    repository: _SessionRepositoryStub | None = None,
    runner: _SessionRunnerStub | None = None,
    quota_service: _UserMessageQuotaServiceStub | None = None,
    title_generator: _SessionTitleGeneratorStub | None = None,
) -> SessionConversationService:
    return SessionConversationService(
        session_repository=repository or _SessionRepositoryStub(),
        runner=runner or _SessionRunnerStub(),
        user_message_rate_limit_service=quota_service or _UserMessageQuotaServiceStub(),
        title_generator=title_generator or _SessionTitleGeneratorStub(),
    )


async def _collect_events(iterator):
    return [event async for event in iterator]


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
    def test_creates_session_with_pending_empty_title(self) -> None:
        owner_id = uuid4()
        initial_prompt = "spiele was ruhiges"
        repository = _SessionRepositoryStub()
        service = _make_management_service(repository=repository)

        created = asyncio.run(
            service.create(owner_id=owner_id, initial_prompt=initial_prompt)
        )

        assert created is repository.created_session
        assert created.title == ""
        assert created.owner_id == owner_id
        assert len(created.entries) == 0
        assert created.phase == Phase.ONBOARDING


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
        track = session.add_track(title="Starlight", artist="Muse", year=2006)
        repository = _SessionRepositoryStub(session_by_id=session)
        service = _make_management_service(repository=repository)

        result = asyncio.run(
            service.pin_playlist_track(
                session_id=session.id,
                user_id=owner_id,
                track_id=track.id,
            )
        )

        assert result is track
        assert track.is_pinned is True
        assert repository.saved_sessions == [session]

    def test_unlocks_playlist_track_and_persists(self) -> None:
        owner_id = uuid4()
        session = Session(title="Roadtrip", entries=[], owner_id=owner_id)
        track = session.add_track(
            title="Starlight", artist="Muse", year=2006, is_pinned=True
        )
        repository = _SessionRepositoryStub(session_by_id=session)
        service = _make_management_service(repository=repository)

        result = asyncio.run(
            service.unpin_playlist_track(
                session_id=session.id,
                user_id=owner_id,
                track_id=track.id,
            )
        )

        assert result is track
        assert track.is_pinned is False
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
        quota_service = _UserMessageQuotaServiceStub()
        service = _make_conversation_service(
            repository=repository,
            runner=runner,
            quota_service=quota_service,
        )

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
        assert quota_service.consumed_user_ids == [owner_id]

    def test_generates_title_for_untitled_session_during_message_stream(self) -> None:
        owner_id = uuid4()
        prompt = "spiele was ruhiges"
        session = Session(title="", entries=[], owner_id=owner_id)
        repository = _SessionRepositoryStub(session_by_id=session)
        generator = _SessionTitleGeneratorStub(generated_title=f"  {'A' * 130}  ")
        service = _make_conversation_service(
            repository=repository,
            title_generator=generator,
        )

        events = asyncio.run(
            _collect_events(
                service.send_message(
                    session_id=session.id,
                    user_id=owner_id,
                    content=prompt,
                )
            )
        )

        title_events = [
            event for event in events if isinstance(event, SessionTitleGenerated)
        ]
        assert title_events == [SessionTitleGenerated(title="A" * 120)]
        assert session.title == "A" * 120
        assert generator.received_initial_prompt == prompt
        assert generator.call_count == 1
        assert any(
            isinstance(event, SessionAssistantMessageCompleted) for event in events
        )

    def test_does_not_generate_title_for_already_titled_session(self) -> None:
        owner_id = uuid4()
        session = Session(title="Rihanna Deck", entries=[], owner_id=owner_id)
        generator = _SessionTitleGeneratorStub(generated_title="New Title")
        service = _make_conversation_service(
            repository=_SessionRepositoryStub(session_by_id=session),
            title_generator=generator,
        )

        events = asyncio.run(
            _collect_events(
                service.send_message(
                    session_id=session.id,
                    user_id=owner_id,
                    content="spiele rihanna hits",
                )
            )
        )

        assert not any(isinstance(event, SessionTitleGenerated) for event in events)
        assert session.title == "Rihanna Deck"
        assert generator.call_count == 0

    def test_title_generator_error_falls_back_without_breaking_stream(self) -> None:
        owner_id = uuid4()
        session = Session(title="", entries=[], owner_id=owner_id)
        generator = _SessionTitleGeneratorStub(error=RuntimeError("title failed"))
        service = _make_conversation_service(
            repository=_SessionRepositoryStub(session_by_id=session),
            title_generator=generator,
        )

        events = asyncio.run(
            _collect_events(
                service.send_message(
                    session_id=session.id,
                    user_id=owner_id,
                    content="spiele rihanna hits",
                )
            )
        )

        assert SessionTitleGenerated(title="New Session") in events
        assert session.title == "New Session"
        assert any(
            isinstance(event, SessionAssistantMessageCompleted) for event in events
        )

    def test_does_not_persist_when_quota_is_exceeded(self) -> None:
        owner_id = uuid4()
        session = Session(title="Rihanna Deck", entries=[], owner_id=owner_id)
        repository = _SessionRepositoryStub(session_by_id=session)
        quota_error = UserMessageQuotaExceededError(
            limit=50,
            reset_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        service = _make_conversation_service(
            repository=repository,
            quota_service=_UserMessageQuotaServiceStub(error=quota_error),
        )

        with pytest.raises(UserMessageQuotaExceededError):
            asyncio.run(
                _collect_events(
                    service.send_message(
                        session_id=session.id,
                        user_id=owner_id,
                        content="spiele rihanna hits",
                    )
                )
            )

        user_messages = [
            entry for entry in session.entries if isinstance(entry, UserMessage)
        ]
        assert user_messages == []
        assert repository.saved_sessions == []

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
        track = PlaylistTrack(id=uuid4(), title="Take On Me", artist="a-ha", year=1985)
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

    def test_emits_playlist_set_for_initial_runner_track_addition(self) -> None:
        owner_id = uuid4()
        playlist_id = uuid4()
        track = PlaylistTrack(id=uuid4(), title="Take On Me", artist="a-ha", year=1985)
        session = Session(title="Roadtrip", entries=[], owner_id=owner_id)
        runner = _SessionRunnerStub(
            events=[
                SessionRunnerPlaylistTracksAdded(
                    playlist_id=playlist_id,
                    tracks=[track],
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
                    content="leg den song ins deck",
                )
            )
        )

        playlist_event = next(
            event for event in events if isinstance(event, SessionPlaylistSet)
        )
        assert playlist_event.playlist.id == playlist_id
        assert playlist_event.playlist.tracks == [track]
        assert not any(isinstance(event, SessionPlaylistTrackAdded) for event in events)
        assert session.playlist is not None
        assert session.playlist.id == playlist_id

    def test_emits_playlist_track_diffs_for_runner_playlist_mutations(self) -> None:
        owner_id = uuid4()
        playlist_id = uuid4()
        removed_track = PlaylistTrack(
            id=uuid4(),
            title="Take On Me",
            artist="a-ha",
            year=1985,
        )
        added_track = PlaylistTrack(
            id=uuid4(),
            title="Billie Jean",
            artist="Michael Jackson",
            year=1982,
        )
        replacement_track = PlaylistTrack(
            id=uuid4(),
            title="Africa",
            artist="Toto",
            year=1982,
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

    def test_persists_partial_assistant_message_when_runner_is_cancelled(self) -> None:
        owner_id = uuid4()
        session = Session(title="Roadtrip", entries=[], owner_id=owner_id)
        repository = _SessionRepositoryStub(session_by_id=session)
        runner = _SessionRunnerStub(
            events=[
                SessionRunnerAssistantMessageChunk(chunk="Hi"),
                SessionRunnerCancelled(),
            ]
        )
        service = _make_conversation_service(repository=repository, runner=runner)

        events = asyncio.run(
            _collect_events(
                service.send_message(
                    session_id=session.id,
                    user_id=owner_id,
                    content="weiter",
                )
            )
        )

        assert any(
            isinstance(event, SessionAssistantMessageCancelled) for event in events
        )
        assistant_messages = [
            entry for entry in session.entries if isinstance(entry, AssistantMessage)
        ]
        assert len(assistant_messages) == 1
        assert assistant_messages[0].content == "Hi"
        assert len(repository.saved_sessions) == 3

    def test_removes_pending_tool_call_when_runner_is_cancelled(self) -> None:
        owner_id = uuid4()
        session = Session(title="Roadtrip", entries=[], owner_id=owner_id)
        pending_call = PendingCall(
            id="call-1",
            function=ToolFunction(name="search_tracks", arguments={"query": "ski"}),
        )
        repository = _SessionRepositoryStub(session_by_id=session)
        runner = _SessionRunnerStub(
            events=[
                SessionRunnerToolCallStarted(call=pending_call),
                SessionRunnerCancelled(),
            ]
        )
        service = _make_conversation_service(repository=repository, runner=runner)

        asyncio.run(
            _collect_events(
                service.send_message(
                    session_id=session.id,
                    user_id=owner_id,
                    content="weiter",
                )
            )
        )

        assert [
            entry for entry in session.entries if isinstance(entry, ToolCallSequence)
        ] == []
        assert len(repository.saved_sessions) == 3

    def test_stop_message_delegates_to_runner(self) -> None:
        owner_id = uuid4()
        session = Session(title="Roadtrip", entries=[], owner_id=owner_id)
        repository = _SessionRepositoryStub(session_by_id=session)
        runner = _SessionRunnerStub()
        service = _make_conversation_service(repository=repository, runner=runner)

        stopped = asyncio.run(
            service.stop_message(session_id=session.id, user_id=owner_id)
        )

        assert stopped is True
        assert runner.stopped_session_ids == [session.id]

    def test_submit_onboarding_answer_persists_and_resumes_runner(self) -> None:
        owner_id = uuid4()
        session = Session(title="Roadtrip", entries=[], owner_id=owner_id)
        question = session.add_onboarding_question(
            question_text="Fuer wen ist die Playlist?",
            options=("Freunde", "Familie"),
        )
        runner = _SessionRunnerStub(
            events=[
                SessionRunnerSuspendedForInput(
                    question="Welche Dekade?",
                    options=["80er", "90er"],
                )
            ]
        )
        repository = _SessionRepositoryStub(session_by_id=session)
        service = _make_conversation_service(repository=repository, runner=runner)

        events = asyncio.run(
            _collect_events(
                service.submit_onboarding_answer(
                    session_id=session.id,
                    user_id=owner_id,
                    question_id=question.id,
                    answer="Freunde",
                )
            )
        )

        assert question.is_answered is True
        assert question.answer == "Freunde"
        assert any(
            isinstance(event, SessionSuspendedForInput)
            and event.kind == SuspensionKind.ONBOARDING_QUESTION
            for event in events
        )

    def test_persists_intermediate_onboarding_question_without_suspending(self) -> None:
        owner_id = uuid4()
        session = Session(title="Roadtrip", entries=[], owner_id=owner_id)
        runner = _SessionRunnerStub(
            events=[
                SessionRunnerQuestionAsked(
                    question="Fuer wen ist die Playlist?",
                    options=["Freunde", "Familie"],
                ),
                SessionRunnerSuspendedForInput(
                    question="Welche Dekade?",
                    options=["80er", "90er"],
                    is_last_question=True,
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
                    content="baue eine playlist",
                )
            )
        )

        assert [
            question.question_text for question in session.onboarding_questions
        ] == [
            "Fuer wen ist die Playlist?",
            "Welche Dekade?",
        ]
        assert [
            question.is_last_question for question in session.onboarding_questions
        ] == [
            False,
            True,
        ]
        suspended_events = [
            event for event in events if isinstance(event, SessionSuspendedForInput)
        ]
        question_events = [
            event
            for event in events
            if isinstance(event, SessionOnboardingQuestionAsked)
        ]
        assert len(question_events) == 1
        assert question_events[0].question == "Fuer wen ist die Playlist?"
        assert question_events[0].options == [
            "Freunde",
            "Familie",
            DECIDE_FOR_ME_OPTION,
        ]
        assert len(suspended_events) == 1
        assert suspended_events[0].question == "Welche Dekade?"
        assert suspended_events[0].options == ["80er", "90er", DECIDE_FOR_ME_OPTION]

    def test_onboarding_tool_call_events_are_not_persisted_or_emitted(self) -> None:
        owner_id = uuid4()
        session = Session(title="Roadtrip", entries=[], owner_id=owner_id)
        onboarding_call = PendingCall(
            id="call-onboarding",
            function=ToolFunction(
                name="ask_onboarding_question",
                arguments={"question": "Fuer wen ist die Playlist?"},
                is_onboarding_question=True,
            ),
        )
        runner = _SessionRunnerStub(
            events=[
                SessionRunnerToolCallStarted(call=onboarding_call),
                SessionRunnerToolCallCompleted(
                    tool_call_id="call-onboarding",
                    result="Frage gestellt",
                ),
                SessionRunnerQuestionAsked(
                    question="Fuer wen ist die Playlist?",
                    options=["Freunde", "Familie"],
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
                    content="baue eine playlist",
                )
            )
        )

        assert [
            entry for entry in session.entries if isinstance(entry, ToolCallSequence)
        ] == []
        assert not any(
            isinstance(event, SessionToolCallSequenceAdded) for event in events
        )
        assert not any(isinstance(event, SessionToolCallResolved) for event in events)
        question_events = [
            event
            for event in events
            if isinstance(event, SessionOnboardingQuestionAsked)
        ]
        assert len(question_events) == 1
        assert question_events[0].question_id == session.onboarding_questions[0].id

    def test_submit_onboarding_answer_for_last_question_persists_without_advancing_phase(
        self,
    ) -> None:
        owner_id = uuid4()
        session = Session(title="Roadtrip", entries=[], owner_id=owner_id)
        question = session.add_onboarding_question(
            question_text="Letzte Frage?",
            options=("Ja",),
            is_last_question=True,
        )
        repository = _SessionRepositoryStub(session_by_id=session)
        service = _make_conversation_service(repository=repository)

        events = asyncio.run(
            _collect_events(
                service.submit_onboarding_answer(
                    session_id=session.id,
                    user_id=owner_id,
                    question_id=question.id,
                    answer="Ja",
                )
            )
        )

        assert question.is_answered is True
        assert session.phase == Phase.ONBOARDING
        assert events == []
        assert repository.saved_sessions == [session]

    def test_complete_onboarding_advances_phase_and_emits_playlist_context(
        self,
    ) -> None:
        owner_id = uuid4()
        session = Session(title="Roadtrip", entries=[], owner_id=owner_id)
        question = session.add_onboarding_question(
            question_text="Letzte Frage?",
            options=("Ja",),
            is_last_question=True,
        )
        session.answer_onboarding_question(question_id=question.id, answer="Ja")
        runner = _SessionRunnerStub(events=[])
        repository = _SessionRepositoryStub(session_by_id=session)
        service = _make_conversation_service(repository=repository, runner=runner)

        events = asyncio.run(
            _collect_events(
                service.complete_onboarding(
                    session_id=session.id,
                    user_id=owner_id,
                )
            )
        )

        assert session.phase == Phase.BUILD
        assert events == [
            SessionSuspendedForInput(kind=SuspensionKind.PLAYLIST_CONTEXT)
        ]

    def test_complete_onboarding_rejects_unanswered_questions(self) -> None:
        owner_id = uuid4()
        session = Session(title="Roadtrip", entries=[], owner_id=owner_id)
        session.add_onboarding_question(
            question_text="Fuer wen ist die Playlist?",
            options=("Freunde", "Familie"),
        )
        repository = _SessionRepositoryStub(session_by_id=session)
        service = _make_conversation_service(repository=repository)

        with pytest.raises(
            InvalidSessionPhaseTransitionError,
            match="onboarding questions are unanswered",
        ):
            asyncio.run(
                _collect_events(
                    service.complete_onboarding(
                        session_id=session.id,
                        user_id=owner_id,
                    )
                )
            )

        assert session.phase == Phase.ONBOARDING
