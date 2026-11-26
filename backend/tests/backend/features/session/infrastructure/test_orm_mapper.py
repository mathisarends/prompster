from datetime import UTC, datetime, timedelta
from uuid import UUID

from backend.features.session.domain import (
    ImageAttachment,
    OnboardingQuestionSelectionMode,
    PendingCall,
    Phase,
    Session,
    ToolActionType,
    ToolCallSequence,
    ToolFunction,
    UserCurationEvent,
    UserCurationEventType,
    UserMessage,
    UserMessageAttachment,
    UserMessageAttachmentKind,
)
from backend.features.session.infrastructure.orm_mapper import SessionOrmMapper
from backend.platform.database.orm import (
    SessionArtistReferenceModel,
    SessionModel,
    SessionOnboardingQuestionModel,
    SessionPlaylistReferenceModel,
    SessionUserCurationEventModel,
    SessionUserMessageAttachmentModel,
    SessionUserMessageImageAttachmentModel,
    SessionUserMessageModel,
)

_TEST_TIME = datetime(2024, 1, 1, tzinfo=UTC)


def _session_model(session: Session, **relationships: object) -> SessionModel:
    return SessionModel(
        id=session.id,
        title=session.title,
        owner_id=session.owner_id,
        is_starred=False,
        last_activity_at=session.created_at,
        created_at=session.created_at,
        **relationships,
    )


def _restored_message(
    mapper: SessionOrmMapper,
    session: Session,
    row: SessionUserMessageModel,
) -> UserMessage:
    restored = mapper.to_domain(_session_model(session, user_messages=[row]))
    message = restored.entries[0]
    assert isinstance(message, UserMessage)
    return message


def test_sync_entries_reuses_existing_user_message_row_by_id() -> None:
    owner_id = UUID(int=1)
    session_id = UUID(int=2)

    session = Session.restore(
        title="Roadtrip",
        entries=[],
        owner_id=owner_id,
        id=session_id,
        created_at=_TEST_TIME,
    )
    session.add_user_message("hello")
    message = session.entries[0]
    assert isinstance(message, UserMessage)
    message_id = message.id

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

    mapper = SessionOrmMapper()
    mapper.sync(orm=orm, session=session)

    assert len(orm.user_messages) == 1
    assert orm.user_messages[0] is existing_row
    assert orm.user_messages[0].content == "hello"


def test_user_message_attachment_mapping_roundtrip() -> None:
    owner_id = UUID(int=3)
    session_id = UUID(int=4)
    attachment = UserMessageAttachment(
        kind=UserMessageAttachmentKind.SPOTIFY_PLAYLIST,
        external_id="37i9dQZF1DX4dyzvuaRJ0n",
        title="Lo-Fi Beats",
        subtitle="Spotify",
        image_url="https://example.com/image.jpg",
        spotify_id="37i9dQZF1DX4dyzvuaRJ0n",
    )

    session = Session.restore(
        title="Roadtrip",
        entries=[],
        owner_id=owner_id,
        id=session_id,
        created_at=_TEST_TIME,
    )
    session.add_user_message("nutze diese playlist", attachments=[attachment])
    message = session.entries[0]
    assert isinstance(message, UserMessage)
    message_id = message.id

    mapper = SessionOrmMapper()
    orm_message = mapper.to_orm(session).user_messages[0]

    assert len(orm_message.attachments) == 1
    assert orm_message.attachments[0].kind == "spotify-playlist"
    assert orm_message.attachments[0].external_id == "37i9dQZF1DX4dyzvuaRJ0n"

    domain_message = _restored_message(
        mapper,
        session,
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
        ),
    )

    assert len(domain_message.attachments) == 1
    assert (
        domain_message.attachments[0].kind == UserMessageAttachmentKind.SPOTIFY_PLAYLIST
    )
    assert domain_message.attachments[0].title == "Lo-Fi Beats"


def test_user_message_image_attachment_mapping_roundtrip() -> None:
    owner_id = UUID(int=5)
    session_id = UUID(int=6)
    image_attachment_id = UUID(int=7)

    session = Session.restore(
        title="Roadtrip",
        entries=[],
        owner_id=owner_id,
        id=session_id,
        created_at=_TEST_TIME,
    )
    session.add_user_message(
        "analysiere den screenshot",
        image_attachments=[
            ImageAttachment.restore(
                id=image_attachment_id,
                created_at=_TEST_TIME,
                storage_key=(
                    f"sessions/abc/messages/def/attachments/{image_attachment_id}.png"
                ),
                content_type="image/png",
                file_name="screenshot.png",
                size_bytes=2048,
            )
        ],
    )
    message = session.entries[0]
    assert isinstance(message, UserMessage)
    message_id = message.id

    mapper = SessionOrmMapper()
    orm_message = mapper.to_orm(session).user_messages[0]

    assert len(orm_message.image_attachments) == 1
    assert orm_message.image_attachments[0].storage_key.endswith(".png")
    assert orm_message.image_attachments[0].content_type == "image/png"

    domain_message = _restored_message(
        mapper,
        session,
        SessionUserMessageModel(
            id=message_id,
            session_id=session_id,
            position=0,
            content="analysiere den screenshot",
            created_at=message.created_at,
            attachments=[],
            image_attachments=[
                SessionUserMessageImageAttachmentModel(
                    id=image_attachment_id,
                    user_message_id=message_id,
                    storage_key=(
                        "sessions/abc/messages/def/attachments/"
                        f"{image_attachment_id}.png"
                    ),
                    content_type="image/png",
                    file_name="screenshot.png",
                    size_bytes=2048,
                    created_at=message.created_at,
                )
            ],
        ),
    )

    assert len(domain_message.image_attachments) == 1
    assert domain_message.image_attachments[0].file_name == "screenshot.png"
    assert domain_message.image_attachments[0].size_bytes == 2048


def test_session_phase_mapping_roundtrip() -> None:
    owner_id = UUID(int=8)
    session_id = UUID(int=9)
    mapper = SessionOrmMapper()
    session = Session.restore(
        title="Roadtrip",
        entries=[],
        owner_id=owner_id,
        id=session_id,
        created_at=_TEST_TIME,
        phase=Phase.BUILD,
    )

    orm = mapper.to_orm(session)

    assert orm.phase == "build"

    orm.user_messages = []
    orm.assistant_messages = []
    orm.tool_call_sequences = []
    orm.user_curation_events = []
    orm.playlist_references = []
    orm.artist_references = []
    mapped = mapper.to_domain(orm)

    assert mapped.phase == Phase.BUILD


def test_sync_user_curation_events_reuses_existing_row_by_id() -> None:
    owner_id = UUID(int=10)
    session_id = UUID(int=11)
    event = UserCurationEvent.create(
        event_type=UserCurationEventType.TRACK_ADDED,
        track_id=UUID(int=12),
        track_title="Starlight",
        track_artist="Muse",
        track_year=2006,
        track_spotify_uri="spotify:track:abc",
        track_cover_url="https://example.com/cover.jpg",
    )
    session = Session.restore(
        title="Roadtrip",
        entries=[],
        owner_id=owner_id,
        id=session_id,
        created_at=_TEST_TIME,
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
        track_id=UUID(int=13),
        track_title="old",
        track_artist="old",
        track_spotify_uri=None,
        track_year=1999,
        consumed=True,
        created_at=event.created_at,
    )
    orm.user_curation_events = [existing_row]

    mapper = SessionOrmMapper()
    mapper.sync(orm=orm, session=session)

    assert len(orm.user_curation_events) == 1
    assert orm.user_curation_events[0] is existing_row
    assert orm.user_curation_events[0].event_type == "track_added"
    assert orm.user_curation_events[0].track_title == "Starlight"
    assert (
        orm.user_curation_events[0].track_cover_url == "https://example.com/cover.jpg"
    )
    assert orm.user_curation_events[0].track_year == 2006
    assert orm.user_curation_events[0].consumed is False


def test_reference_mapping_roundtrip() -> None:
    owner_id = UUID(int=14)
    session_id = UUID(int=15)
    session = Session.restore(
        title="Roadtrip",
        entries=[],
        owner_id=owner_id,
        id=session_id,
        created_at=_TEST_TIME,
    )
    playlist_reference = session.add_playlist_reference(
        spotify_playlist_id="37i9dQZF1DX4dyzvuaRJ0n",
        name="Lo-Fi Beats",
        owner="Spotify",
        cover_url="https://example.com/playlist.jpg",
        total_tracks=100,
    )
    artist_reference = session.add_artist_reference(
        spotify_artist_id="1dfeR4HaWDbWqFHLkxsg1d",
        name="Queen",
        image_url="https://example.com/queen.jpg",
        genres=("rock", "glam rock"),
        followers=50_000_000,
        popularity=81,
    )

    orm = SessionModel(
        id=session_id,
        title=session.title,
        owner_id=session.owner_id,
        is_starred=False,
        last_activity_at=session.created_at,
        created_at=session.created_at,
    )
    mapper = SessionOrmMapper()
    mapper.sync(orm=orm, session=session)

    assert len(orm.playlist_references) == 1
    assert orm.playlist_references[0].id == playlist_reference.id
    assert orm.playlist_references[0].spotify_playlist_id == ("37i9dQZF1DX4dyzvuaRJ0n")
    assert len(orm.artist_references) == 1
    assert orm.artist_references[0].id == artist_reference.id
    assert orm.artist_references[0].genres == ["rock", "glam rock"]

    restored = mapper.to_domain(
        _session_model(
            session,
            playlist_references=[
                SessionPlaylistReferenceModel(
                    id=playlist_reference.id,
                    session_id=session_id,
                    position=0,
                    spotify_playlist_id="37i9dQZF1DX4dyzvuaRJ0n",
                    name="Lo-Fi Beats",
                    owner="Spotify",
                    cover_url="https://example.com/playlist.jpg",
                    total_tracks=100,
                    created_at=playlist_reference.created_at,
                )
            ],
            artist_references=[
                SessionArtistReferenceModel(
                    id=artist_reference.id,
                    session_id=session_id,
                    position=0,
                    spotify_artist_id="1dfeR4HaWDbWqFHLkxsg1d",
                    name="Queen",
                    image_url="https://example.com/queen.jpg",
                    genres=["rock", "glam rock"],
                    followers=50_000_000,
                    popularity=81,
                    created_at=artist_reference.created_at,
                )
            ],
        )
    )
    mapped_playlist = restored.playlist_references[0]
    mapped_artist = restored.artist_references[0]

    assert mapped_playlist.id == playlist_reference.id
    assert mapped_playlist.total_tracks == 100
    assert mapped_artist.id == artist_reference.id
    assert mapped_artist.genres == ("rock", "glam rock")


def test_resolve_last_activity_at_includes_user_curation_events() -> None:
    owner_id = UUID(int=16)
    session = Session.create(title="Roadtrip", owner_id=owner_id)
    session.add_track(title="Starlight", artist="Muse", year=2006)
    session.user_curation_events[0].created_at = session.created_at + timedelta(
        minutes=5
    )

    mapper = SessionOrmMapper()
    last_activity = mapper.to_orm(session).last_activity_at

    assert last_activity == session.user_curation_events[0].created_at


def test_resolve_last_activity_at_includes_references() -> None:
    owner_id = UUID(int=17)
    session = Session.create(title="Roadtrip", owner_id=owner_id)
    reference = session.add_artist_reference(
        spotify_artist_id="1dfeR4HaWDbWqFHLkxsg1d",
        name="Queen",
    )
    reference.created_at = session.created_at + timedelta(minutes=5)

    mapper = SessionOrmMapper()
    last_activity = mapper.to_orm(session).last_activity_at

    assert last_activity == reference.created_at


def test_user_curation_event_mapping_roundtrip() -> None:
    mapper = SessionOrmMapper()
    session = Session.create(title="Roadtrip", owner_id=UUID(int=18))
    event = UserCurationEvent.create(
        event_type=UserCurationEventType.TRACK_ADDED,
        track_id=UUID(int=19),
        track_title="Starlight",
        track_artist="Muse",
        track_year=2006,
        track_spotify_uri="spotify:track:abc",
        track_cover_url="https://example.com/cover.jpg",
    )
    row = SessionUserCurationEventModel(
        id=event.id,
        session_id=session.id,
        position=3,
        event_type=event.event_type.value,
        track_id=event.track_id,
        track_title=event.track_title,
        track_artist=event.track_artist,
        track_spotify_uri=event.track_spotify_uri,
        track_cover_url=event.track_cover_url,
        track_year=event.track_year,
        consumed=False,
        created_at=event.created_at,
    )

    restored = mapper.to_domain(_session_model(session, user_curation_events=[row]))
    mapped = restored.user_curation_events[0]

    assert mapped.id == event.id
    assert mapped.event_type == UserCurationEventType.TRACK_ADDED
    assert mapped.track_id == event.track_id
    assert mapped.track_title == "Starlight"
    assert mapped.track_artist == "Muse"
    assert mapped.track_spotify_uri == "spotify:track:abc"
    assert mapped.track_cover_url == "https://example.com/cover.jpg"
    assert mapped.track_year == 2006


def test_to_domain_hydrates_user_message_curation_events() -> None:
    mapper = SessionOrmMapper()
    owner_id = UUID(int=20)
    session_id = UUID(int=21)
    message_id = UUID(int=22)
    message_created_at = datetime(2026, 1, 1, tzinfo=UTC)
    event_created_at = message_created_at - timedelta(seconds=5)

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
    orm.user_curation_events = [
        SessionUserCurationEventModel(
            id=UUID(int=23),
            session_id=session_id,
            position=0,
            event_type=UserCurationEventType.TRACK_ADDED.value,
            track_id=UUID(int=24),
            track_title="Starlight",
            track_artist="Muse",
            track_year=2006,
            consumed=False,
            created_at=event_created_at,
        )
    ]
    orm.playlist_references = [
        SessionPlaylistReferenceModel(
            id=UUID(int=25),
            session_id=session_id,
            position=0,
            spotify_playlist_id="b",
            name="Second",
            total_tracks=20,
            created_at=message_created_at,
        ),
        SessionPlaylistReferenceModel(
            id=UUID(int=26),
            session_id=session_id,
            position=1,
            spotify_playlist_id="a",
            name="First",
            total_tracks=10,
            created_at=message_created_at,
        ),
    ]
    orm.artist_references = [
        SessionArtistReferenceModel(
            id=UUID(int=27),
            session_id=session_id,
            position=0,
            spotify_artist_id="artist",
            name="Queen",
            genres=["rock"],
            created_at=message_created_at,
        )
    ]

    mapped = mapper.to_domain(orm)

    message = mapped.entries[0]
    assert isinstance(message, UserMessage)
    assert len(message.user_curation_events) == 1
    assert (
        message.user_curation_events[0].event_type == UserCurationEventType.TRACK_ADDED
    )
    assert message.user_curation_events[0].track_year == 2006
    assert [reference.name for reference in mapped.playlist_references] == [
        "Second",
        "First",
    ]
    assert mapped.artist_references[0].genres == ("rock",)


def test_tool_call_action_type_mapping_roundtrip() -> None:
    mapper = SessionOrmMapper()
    call = PendingCall(
        id="call-1",
        function=ToolFunction(
            name="search_tracks",
            arguments={"query": "abba"},
            status_label="Suche nach 'Abba'",
            action_type=ToolActionType.SEARCH_TRACKS,
            is_onboarding_question=True,
        ),
    )

    session = Session.create(title="Roadtrip", owner_id=UUID(int=28))
    session.add_tool_call(call)

    orm = mapper.to_orm(session)
    orm_call = orm.tool_call_sequences[0].calls[0]

    assert orm_call.function_action_type == "search_tracks"
    assert orm_call.function_is_onboarding_question is True

    restored_sequence = mapper.to_domain(orm).entries[0]
    assert isinstance(restored_sequence, ToolCallSequence)
    mapped_call = restored_sequence.calls[0]

    assert mapped_call.function.action_type == ToolActionType.SEARCH_TRACKS
    assert mapped_call.function.is_onboarding_question is True


def test_onboarding_question_mapping_roundtrip() -> None:
    owner_id = UUID(int=29)
    session_id = UUID(int=30)
    session = Session.restore(
        title="Roadtrip",
        entries=[],
        owner_id=owner_id,
        id=session_id,
        created_at=_TEST_TIME,
    )
    question = session.add_onboarding_question(
        question_text="Fuer wen ist die Playlist?",
        hint="Enge Zielgruppen machen das Deck spitzer.",
        options=("Freunde", "Familie"),
        selection_mode=OnboardingQuestionSelectionMode.MULTI_SELECT,
    )
    session.answer_onboarding_question(
        question_id=question.id,
        answers=["Freunde", "Familie"],
    )

    mapper = SessionOrmMapper()
    orm = SessionModel(
        id=session_id,
        title=session.title,
        owner_id=session.owner_id,
        is_starred=False,
        last_activity_at=session.created_at,
        created_at=session.created_at,
    )
    orm.user_messages = []
    orm.assistant_messages = []
    orm.tool_call_sequences = []
    orm.user_curation_events = []
    orm.playlist_references = []
    orm.artist_references = []
    mapper.sync(orm=orm, session=session)

    assert len(orm.onboarding_questions) == 1
    assert orm.onboarding_questions[0].question_text == "Fuer wen ist die Playlist?"
    assert (
        orm.onboarding_questions[0].hint == "Enge Zielgruppen machen das Deck spitzer."
    )
    assert orm.onboarding_questions[0].selection_mode == "multi_select"
    assert orm.onboarding_questions[0].answer == "Freunde, Familie"
    assert orm.onboarding_questions[0].answers == ["Freunde", "Familie"]
    assert orm.onboarding_questions[0].is_answered is True

    restored = mapper.to_domain(
        _session_model(
            session,
            onboarding_questions=[
                SessionOnboardingQuestionModel(
                    id=question.id,
                    session_id=session_id,
                    sequence_number=1,
                    question_text="Fuer wen ist die Playlist?",
                    hint="Enge Zielgruppen machen das Deck spitzer.",
                    options=["Freunde", "Familie"],
                    selection_mode="multi_select",
                    answers=["Freunde", "Familie"],
                    answer="Freunde, Familie",
                    is_answered=True,
                    answered_at=question.answered_at,
                    created_at=question.created_at,
                )
            ],
        )
    )
    mapped = restored.onboarding_questions[0]

    assert mapped.id == question.id
    assert mapped.sequence_number == 1
    assert mapped.hint == "Enge Zielgruppen machen das Deck spitzer."
    assert mapped.options == ("Freunde", "Familie")
    assert mapped.selection_mode == OnboardingQuestionSelectionMode.MULTI_SELECT
    assert mapped.answers == ("Freunde", "Familie")
