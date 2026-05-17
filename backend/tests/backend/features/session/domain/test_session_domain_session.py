from uuid import UUID, uuid4

import pytest

from backend.features.session.domain.exceptions import (
    NoPendingToolCallGroupError,
    PendingToolCallsError,
    PlaylistTrackNotFoundError,
    SessionAccessDeniedError,
)
from backend.features.session.domain.session import Session
from backend.features.session.domain.views import ToolCall, ToolFunction


@pytest.fixture
def owner_id() -> UUID:
    return uuid4()


@pytest.fixture
def session(owner_id: UUID) -> Session:
    return Session(title="Roadtrip", messages=[], owner_id=owner_id)


class TestSessionDomainSession:
    def test_messages_property_is_immutable(self, session: Session) -> None:
        assert isinstance(session.messages, tuple)

        with pytest.raises(AttributeError, match="append"):
            session.messages.append(object())

    def test_add_user_message_appends_internal_messages(self, session: Session) -> None:
        created = session.add_user_message("play something chill")

        assert len(session.messages) == 1
        assert session.messages[0] is created

    def test_add_user_message_raises_when_tool_calls_pending(
        self, session: Session
    ) -> None:
        pending_call = ToolCall(
            id="tc-1",
            function=ToolFunction(
                name="search_track", arguments={"query": "daft punk"}
            ),
        )
        session.add_assistant_message(
            content="Ich suche Tracks...", tool_calls=[pending_call]
        )

        with pytest.raises(PendingToolCallsError, match="tool calls are pending"):
            session.add_user_message("noch ein song")

    def test_set_playlist_assigns_playlist(self, session: Session) -> None:
        playlist = session.set_playlist(tracks=[], name="Favorites")

        assert session.playlist is playlist
        assert session.playlist is not None
        assert session.playlist.name == "Favorites"

    def test_add_track_creates_playlist_if_missing(self, session: Session) -> None:
        track = session.add_track(title="Starlight", artist="Muse", year=2006)

        assert session.playlist is not None
        assert len(session.playlist.tracks) == 1
        assert session.playlist.tracks[0] is track

    def test_remove_track_raises_when_playlist_missing(self, session: Session) -> None:
        with pytest.raises(PlaylistTrackNotFoundError, match="has no playlist"):
            session.remove_track(uuid4())

    def test_resolve_tool_call_raises_without_pending_group(
        self, session: Session
    ) -> None:
        with pytest.raises(
            NoPendingToolCallGroupError, match="no pending tool call group"
        ):
            session.resolve_tool_call("tc-1", "ok")

    def test_has_access_raises_for_non_owner(self, session: Session) -> None:
        with pytest.raises(SessionAccessDeniedError, match="does not have access"):
            session.has_access(uuid4())
