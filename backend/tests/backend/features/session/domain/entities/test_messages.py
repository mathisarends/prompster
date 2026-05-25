from datetime import datetime, timezone
from uuid import uuid4

from backend.features.session.domain import (
    AssistantMessage,
    UserMessage,
    UserMessageAttachment,
    UserMessageAttachmentKind,
)


class TestUserMessage:
    def test_keeps_explicit_identity(self) -> None:
        message_id = uuid4()
        created_time = datetime(2026, 6, 6, tzinfo=timezone.utc)

        message = UserMessage(
            content="hello",
            id=message_id,
            created_time=created_time,
        )

        assert message.id == message_id
        assert message.created_at == created_time
        assert message.content == "hello"

    def test_keeps_attachment_references(self) -> None:
        attachment = UserMessageAttachment(
            kind=UserMessageAttachmentKind.SPOTIFY_PLAYLIST,
            external_id="37i9dQZF1DX4dyzvuaRJ0n",
            title="Lo-Fi Beats",
            subtitle="Spotify",
            image_url="https://example.com/image.jpg",
            spotify_id="37i9dQZF1DX4dyzvuaRJ0n",
        )

        message = UserMessage(content="nutze diese playlist", attachments=[attachment])

        assert len(message.attachments) == 1
        assert message.attachments[0].kind == UserMessageAttachmentKind.SPOTIFY_PLAYLIST
        assert message.attachments[0].external_id == "37i9dQZF1DX4dyzvuaRJ0n"


class TestAssistantMessage:
    def test_defaults_content_to_empty_string(self) -> None:
        message = AssistantMessage()

        assert message.content == ""

    def test_keeps_explicit_identity(self) -> None:
        message_id = uuid4()
        created_time = datetime(2026, 6, 6, tzinfo=timezone.utc)

        message = AssistantMessage(
            content="hi",
            id=message_id,
            created_time=created_time,
        )

        assert message.id == message_id
        assert message.created_at == created_time
        assert message.content == "hi"
