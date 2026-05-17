import asyncio
from uuid import UUID, uuid4

from backend.features.session.application import (
    AddPlaylistTrackHandler,
    AnswerFollowUpWithOptionHandler,
    AnswerFollowUpWithTextHandler,
    AppendUserMessageHandler,
    PersistSessionHandler,
    RemovePlaylistTrackHandler,
    SessionFollowUpAnswered,
    SessionFollowUpSkipped,
    SessionPlaylistSet,
    SessionPlaylistTrackAdded,
    SessionPlaylistTrackRemoved,
    SessionUserMessageAppended,
    SkipFollowUpHandler,
)
from backend.features.session.domain import (
    FollowUpOption,
    FollowUpQuestion,
    MessageRole,
    Session,
    SessionRepository,
)


class _SessionRepositoryStub(SessionRepository):
    def __init__(self) -> None:
        self.saved_sessions: list[Session] = []

    async def get_by_id(self, session_id: UUID) -> Session:
        raise AssertionError("get_by_id is not used in PersistSessionHandler tests")

    async def save(self, *, session: Session) -> Session:
        self.saved_sessions.append(session)
        return session

    async def update(self, session_id: UUID, title: str | None) -> Session:
        raise AssertionError("update is not used in PersistSessionHandler tests")

    async def delete(self, session_id: UUID) -> None:
        raise AssertionError("delete is not used in PersistSessionHandler tests")


def _make_session() -> Session:
    return Session(title="Roadtrip", messages=[], owner_id=uuid4())


def _make_follow_up() -> FollowUpQuestion:
    return FollowUpQuestion(
        question="Welches Genre?",
        options=[
            FollowUpOption(id="house", label="House"),
            FollowUpOption(id="techno", label="Techno"),
        ],
    )


class TestAppendUserMessageHandler:
    def test_handle_appends_message_and_emits_event(self) -> None:
        session = _make_session()
        handler = AppendUserMessageHandler()

        events = asyncio.run(handler.handle(session=session, content="Hi"))

        assert len(events) == 1
        event = events[0]
        assert isinstance(event, SessionUserMessageAppended)
        assert event.message is session.messages[0]
        assert event.message.role == MessageRole.USER
        assert event.message.content == "Hi"


class TestAnswerFollowUpWithOptionHandler:
    def test_handle_answers_question_and_emits_group_id(self) -> None:
        session = _make_session()
        question = _make_follow_up()
        message = session.add_assistant_message(follow_up_questions=[question])
        assert message.follow_up_group is not None
        handler = AnswerFollowUpWithOptionHandler()

        events = asyncio.run(
            handler.handle(
                session=session,
                question_id=question.id,
                option_id="house",
            )
        )

        assert len(events) == 1
        event = events[0]
        assert isinstance(event, SessionFollowUpAnswered)
        assert event.group_id == message.follow_up_group.id
        assert event.question is question
        assert event.question.answer_text == "House"
        assert event.question.answered_option_id == "house"


class TestAnswerFollowUpWithTextHandler:
    def test_handle_answers_question_with_text(self) -> None:
        session = _make_session()
        question = _make_follow_up()
        message = session.add_assistant_message(follow_up_questions=[question])
        assert message.follow_up_group is not None
        handler = AnswerFollowUpWithTextHandler()

        events = asyncio.run(
            handler.handle(
                session=session,
                question_id=question.id,
                text="  chillwave  ",
            )
        )

        assert len(events) == 1
        event = events[0]
        assert isinstance(event, SessionFollowUpAnswered)
        assert event.group_id == message.follow_up_group.id
        assert event.question.answer_text == "chillwave"
        assert event.question.answered_option_id is None


class TestSkipFollowUpHandler:
    def test_handle_skips_question_and_emits_event(self) -> None:
        session = _make_session()
        question = _make_follow_up()
        message = session.add_assistant_message(follow_up_questions=[question])
        assert message.follow_up_group is not None
        handler = SkipFollowUpHandler()

        events = asyncio.run(handler.handle(session=session, question_id=question.id))

        assert len(events) == 1
        event = events[0]
        assert isinstance(event, SessionFollowUpSkipped)
        assert event.group_id == message.follow_up_group.id
        assert event.question_id == question.id


class TestAddPlaylistTrackHandler:
    def test_handle_emits_playlist_set_when_playlist_is_created(self) -> None:
        session = _make_session()
        handler = AddPlaylistTrackHandler()

        events = asyncio.run(
            handler.handle(session=session, title="Starlight", artist="Muse")
        )

        assert len(events) == 1
        event = events[0]
        assert isinstance(event, SessionPlaylistSet)
        assert event.playlist is session.playlist
        assert event.playlist.tracks[0].title == "Starlight"

    def test_handle_emits_track_added_when_playlist_exists(self) -> None:
        session = _make_session()
        session.add_track(title="Teardrop", artist="Massive Attack")
        assert session.playlist is not None
        playlist_id = session.playlist.id
        handler = AddPlaylistTrackHandler()

        events = asyncio.run(
            handler.handle(session=session, title="Starlight", artist="Muse")
        )

        assert len(events) == 1
        event = events[0]
        assert isinstance(event, SessionPlaylistTrackAdded)
        assert event.playlist_id == playlist_id
        assert event.track.title == "Starlight"


class TestRemovePlaylistTrackHandler:
    def test_handle_removes_track_and_emits_event(self) -> None:
        session = _make_session()
        track = session.add_track(title="Starlight", artist="Muse")
        assert session.playlist is not None
        playlist_id = session.playlist.id
        handler = RemovePlaylistTrackHandler()

        events = asyncio.run(handler.handle(session=session, track_id=track.id))

        assert len(events) == 1
        event = events[0]
        assert isinstance(event, SessionPlaylistTrackRemoved)
        assert event.playlist_id == playlist_id
        assert event.track_id == track.id
        assert session.playlist.tracks == []


class TestPersistSessionHandler:
    def test_handle_delegates_to_repository(self) -> None:
        session = _make_session()
        repository = _SessionRepositoryStub()
        handler = PersistSessionHandler(session_repository=repository)

        result = asyncio.run(handler.handle(session=session))

        assert result is session
        assert repository.saved_sessions == [session]
