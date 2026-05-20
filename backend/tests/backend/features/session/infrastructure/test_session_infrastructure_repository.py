from unittest.mock import Mock
from uuid import uuid4

from backend.features.session.domain import Session, UserMessage
from backend.features.session.infrastructure.repository import SqlSessionRepository
from backend.infrastructure.database.orm import SessionModel, SessionUserMessageModel


def test_sync_entries_reuses_existing_user_message_row_by_id() -> None:
    owner_id = uuid4()
    session_id = uuid4()
    message_id = uuid4()

    session = Session(title="Roadtrip", entries=[], owner_id=owner_id, id=session_id)
    session.add_user_message("hello")
    message = session.entries[0]
    assert isinstance(message, UserMessage)
    message.id = message_id

    orm = SessionModel(
        id=session_id,
        title=session.title,
        owner_id=session.owner_id,
        is_starred=False,
        last_activity_at=session.created_at,
        created_at=session.created_at,
    )
    existing_row = SessionUserMessageModel(
        id=message_id,
        session_id=session_id,
        position=0,
        content="stale",
        created_at=message.created_at,
    )
    orm.user_messages = [existing_row]
    orm.assistant_messages = []
    orm.tool_call_groups = []
    orm.follow_up_question_groups = []

    repository = SqlSessionRepository(session=Mock())  # type: ignore[arg-type]
    repository._sync_entries(orm=orm, session_id=session_id, entries=session.entries)

    assert len(orm.user_messages) == 1
    assert orm.user_messages[0] is existing_row
    assert orm.user_messages[0].content == "hello"
