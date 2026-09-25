from datetime import UTC, datetime
from uuid import uuid4

from backend.features.session.domain import (
    AssistantMessage,
    ImageAttachment,
    UserCurationEvent,
    UserCurationEventType,
    UserMessage,
    UserMessageAttachment,
    UserMessageAttachmentKind,
)


class TestUserMessage:
    def test_keeps_explicit_identity(self) -> None:
        message_id = uuid4()
        created_time = datetime(2026, 6, 6, tzinfo=UTC)

        message = UserMessage.restore(
            content="hello",
            id=message_id,
            created_at=created_time,
        )

        assert message.id == message_id
        assert message.created_at == created_time
        assert message.content == "hello"
        assert message.user_curation_events == ()

    def test_keeps_attachment_references(self) -> None:
        attachment = UserMessageAttachment(
            kind=UserMessageAttachmentKind.SPOTIFY_PLAYLIST,
            external_id="37i9dQZF1DX4dyzvuaRJ0n",
            title="Lo-Fi Beats",
            subtitle="Spotify",
            image_url="https://example.com/image.jpg",
            spotify_id="37i9dQZF1DX4dyzvuaRJ0n",
        )

        message = UserMessage.create(
            content="nutze diese playlist", attachments=[attachment]
        )

        assert len(message.attachments) == 1
        assert message.attachments[0].kind == UserMessageAttachmentKind.SPOTIFY_PLAYLIST
        assert message.attachments[0].external_id == "37i9dQZF1DX4dyzvuaRJ0n"

    def test_keeps_user_curation_event_references(self) -> None:
        event = UserCurationEvent.create(
            event_type=UserCurationEventType.TRACK_ADDED,
            track_id=uuid4(),
            track_title="Starlight",
            track_artist="Muse",
        )

        message = UserMessage.create(
            content="fix die playlist", user_curation_events=[event]
        )

        assert len(message.user_curation_events) == 1
        assert message.user_curation_events[0] is event

    def test_keeps_image_attachment_references(self) -> None:
        image = ImageAttachment.create(
            storage_key="sessions/abc/messages/def/attachments/ghi.png",
            content_type="image/png",
            file_name="screenshot.png",
            size_bytes=1024,
        )

        message = UserMessage.create(content="check this", image_attachments=[image])

        assert len(message.image_attachments) == 1
        assert message.image_attachments[0].storage_key.endswith("ghi.png")


class TestAssistantMessage:
    def test_defaults_content_to_empty_string(self) -> None:
        message = AssistantMessage.create()

        assert message.content == ""

    def test_keeps_explicit_identity(self) -> None:
        message_id = uuid4()
        created_time = datetime(2026, 6, 6, tzinfo=UTC)

        message = AssistantMessage.restore(
            content="hi",
            id=message_id,
            created_at=created_time,
        )

        assert message.id == message_id
        assert message.created_at == created_time
        assert message.content == "hi"
