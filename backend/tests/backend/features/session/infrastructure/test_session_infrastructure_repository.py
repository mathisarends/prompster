from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
from uuid import uuid4

from backend.features.session.domain import (
    PendingCall,
    PlaylistTrack,
    Session,
    ToolActionType,
    ToolFunction,
    UserCurationEvent,
    UserCurationEventType,
    UserMessage,
    UserMessageAttachment,
    UserMessageAttachmentKind,
)
from backend.features.session.infrastructure.repository import SqlSessionRepository
from backend.infrastructure.database.orm import (
    PlaylistTrackModel,
    SessionUserCurationEventModel,
    SessionModel,
    SessionUserMessageAttachmentModel,
    SessionUserMessageModel,
)


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
    orm.tool_call_sequences = []
    orm.follow_up_question_groups = []

    repository = SqlSessionRepository(session=Mock())  # type: ignore[arg-type]
    repository._sync_entries(orm=orm, session_id=session_id, entries=session.entries)

    assert len(orm.user_messages) == 1
    assert orm.user_messages[0] is existing_row
    assert orm.user_messages[0].content == "hello"


def test_user_message_attachment_mapping_roundtrip() -> None:
    owner_id = uuid4()
    session_id = uuid4()
    message_id = uuid4()
    attachment = UserMessageAttachment(
        kind=UserMessageAttachmentKind.SPOTIFY_PLAYLIST,
        external_id="37i9dQZF1DX4dyzvuaRJ0n",
        title="Lo-Fi Beats",
        subtitle="Spotify",
        image_url="https://example.com/image.jpg",
        spotify_id="37i9dQZF1DX4dyzvuaRJ0n",
    )

    session = Session(title="Roadtrip", entries=[], owner_id=owner_id, id=session_id)
    session.add_user_message("nutze diese playlist", attachments=[attachment])
    message = session.entries[0]
    assert isinstance(message, UserMessage)
    message.id = message_id

    repository = SqlSessionRepository(session=Mock())  # type: ignore[arg-type]
    orm_message = repository._to_orm_user_message(
        message=message,
        session_id=session_id,
        position=0,
    )

    assert len(orm_message.attachments) == 1
    assert orm_message.attachments[0].kind == "spotify-playlist"
    assert orm_message.attachments[0].external_id == "37i9dQZF1DX4dyzvuaRJ0n"

    domain_message = repository._to_domain_user_message(
        SessionUserMessageModel(
            id=message_id,
            session_id=session_id,
            position=0,
            content="nutze diese playlist",
            created_at=message.created_at,
            attachments=[
                SessionUserMessageAttachmentModel(
                    user_message_id=message_id,
                    position=0,
                    kind="spotify-playlist",
                    external_id="37i9dQZF1DX4dyzvuaRJ0n",
                    title="Lo-Fi Beats",
                    subtitle="Spotify",
                    image_url="https://example.com/image.jpg",
                    spotify_id="37i9dQZF1DX4dyzvuaRJ0n",
                )
            ],
        )
    )

    assert len(domain_message.attachments) == 1
    assert (
        domain_message.attachments[0].kind == UserMessageAttachmentKind.SPOTIFY_PLAYLIST
    )
    assert domain_message.attachments[0].title == "Lo-Fi Beats"


def test_playlist_track_mapping_preserves_lock_state() -> None:
    repository = SqlSessionRepository(session=Mock())  # type: ignore[arg-type]
    playlist_id = uuid4()
    track = PlaylistTrack(
        title="Starlight",
        artist="Muse",
        year=2006,
        spotify_uri="spotify:track:abc",
        cover_url="https://example.com/cover.jpg",
        is_pinned=True,
    )

    orm_track = repository._to_orm_track(
        track=track,
        playlist_id=playlist_id,
        position=0,
    )
    roundtrip = repository._to_domain_track(
        PlaylistTrackModel(
            id=track.id,
            playlist_id=playlist_id,
            position=0,
            title="Starlight",
            artist="Muse",
            year=2006,
            spotify_uri="spotify:track:abc",
            cover_url="https://example.com/cover.jpg",
            is_pinned=True,
            created_at=track.created_at,
        )
    )

    assert orm_track.is_pinned is True
    assert roundtrip.is_pinned is True


def test_sync_user_curation_events_reuses_existing_row_by_id() -> None:
    owner_id = uuid4()
    session_id = uuid4()
    event = UserCurationEvent(
        event_type=UserCurationEventType.TRACK_ADDED,
        track_id=uuid4(),
        track_title="Starlight",
        track_artist="Muse",
        track_spotify_uri="spotify:track:abc",
        track_cover_url="https://example.com/cover.jpg",
        history_index=2,
    )
    session = Session(
        title="Roadtrip",
        entries=[],
        owner_id=owner_id,
        id=session_id,
        user_curation_events=[event],
    )

    orm = SessionModel(
        id=session_id,
        title=session.title,
        owner_id=session.owner_id,
        is_starred=False,
        last_activity_at=session.created_at,
        created_at=session.created_at,
    )
    existing_row = SessionUserCurationEventModel(
        id=event.id,
        session_id=session_id,
        position=0,
        event_type="track_removed",
        track_id=uuid4(),
        track_title="old",
        track_artist="old",
        track_spotify_uri=None,
        history_index=0,
        consumed=True,
        created_at=event.created_at,
    )
    orm.user_curation_events = [existing_row]

    repository = SqlSessionRepository(session=Mock())  # type: ignore[arg-type]
    repository._sync_user_curation_events(
        orm=orm,
        session_id=session_id,
        events=session.user_curation_events,
    )

    assert len(orm.user_curation_events) == 1
    assert orm.user_curation_events[0] is existing_row
    assert orm.user_curation_events[0].event_type == "track_added"
    assert orm.user_curation_events[0].track_title == "Starlight"
    assert (
        orm.user_curation_events[0].track_cover_url == "https://example.com/cover.jpg"
    )
    assert orm.user_curation_events[0].history_index == 2
    assert orm.user_curation_events[0].consumed is False


def test_resolve_last_activity_at_includes_user_curation_events() -> None:
    owner_id = uuid4()
    session = Session(title="Roadtrip", entries=[], owner_id=owner_id)
    session.add_track(title="Starlight", artist="Muse")
    session.user_curation_events[0].created_at = session.created_at + timedelta(
        minutes=5
    )

    repository = SqlSessionRepository(session=Mock())  # type: ignore[arg-type]
    last_activity = repository._resolve_last_activity_at(session)

    assert last_activity == session.user_curation_events[0].created_at


def test_user_curation_event_mapping_roundtrip() -> None:
    repository = SqlSessionRepository(session=Mock())  # type: ignore[arg-type]
    event = UserCurationEvent(
        event_type=UserCurationEventType.TRACK_PINNED,
        track_id=uuid4(),
        track_title="Starlight",
        track_artist="Muse",
        track_spotify_uri="spotify:track:abc",
        track_cover_url="https://example.com/cover.jpg",
        history_index=4,
    )
    row = SessionUserCurationEventModel(
        id=event.id,
        session_id=uuid4(),
        position=3,
        event_type=event.event_type.value,
        track_id=event.track_id,
        track_title=event.track_title,
        track_artist=event.track_artist,
        track_spotify_uri=event.track_spotify_uri,
        track_cover_url=event.track_cover_url,
        history_index=event.history_index,
        consumed=False,
        created_at=event.created_at,
    )

    mapped = repository._to_domain_user_curation_event(row)

    assert mapped.id == event.id
    assert mapped.event_type == UserCurationEventType.TRACK_PINNED
    assert mapped.track_id == event.track_id
    assert mapped.track_title == "Starlight"
    assert mapped.track_artist == "Muse"
    assert mapped.track_spotify_uri == "spotify:track:abc"
    assert mapped.track_cover_url == "https://example.com/cover.jpg"
    assert mapped.history_index == 4


def test_to_domain_hydrates_user_message_curation_events() -> None:
    repository = SqlSessionRepository(session=Mock())  # type: ignore[arg-type]
    owner_id = uuid4()
    session_id = uuid4()
    message_id = uuid4()
    message_created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    event_created_at = message_created_at + timedelta(seconds=5)

    orm = SessionModel(
        id=session_id,
        title="Roadtrip",
        owner_id=owner_id,
        is_starred=False,
        last_activity_at=event_created_at,
        created_at=message_created_at,
    )
    orm.user_messages = [
        SessionUserMessageModel(
            id=message_id,
            session_id=session_id,
            position=0,
            content="weiter",
            created_at=message_created_at,
            attachments=[],
        )
    ]
    orm.assistant_messages = []
    orm.tool_call_sequences = []
    orm.follow_up_question_groups = []
    orm.user_curation_events = [
        SessionUserCurationEventModel(
            id=uuid4(),
            session_id=session_id,
            position=0,
            event_type=UserCurationEventType.TRACK_ADDED.value,
            track_id=uuid4(),
            track_title="Starlight",
            track_artist="Muse",
            history_index=0,
            consumed=False,
            created_at=event_created_at,
        )
    ]

    mapped = repository._to_domain(orm)

    message = mapped.entries[0]
    assert isinstance(message, UserMessage)
    assert len(message.user_curation_events) == 1
    assert (
        message.user_curation_events[0].event_type == UserCurationEventType.TRACK_ADDED
    )
    assert message.user_curation_events[0].history_index == 0


def test_tool_call_action_type_mapping_roundtrip() -> None:
    repository = SqlSessionRepository(session=Mock())  # type: ignore[arg-type]
    sequence_id = uuid4()
    call = PendingCall(
        id="call-1",
        function=ToolFunction(
            name="search_tracks",
            arguments={"query": "abba"},
            status_label="Suche nach 'Abba'",
            action_type=ToolActionType.SEARCH,
        ),
    )

    orm_call = repository._to_orm_tool_call(
        call=call,
        sequence_id=sequence_id,
        position=0,
    )

    assert orm_call.function_action_type == "search"

    mapped_call = repository._to_domain_tool_call(orm_call)

    assert mapped_call.function.action_type == ToolActionType.SEARCH
