import asyncio
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from harnessed.models import ImagePart

from backend.features.session.application.ports import MessageAttachmentStore
from backend.features.session.domain import ImageAttachment, Session
from backend.features.session.infrastructure.agent_history import AgentHistoryBuilder


class _AttachmentStore:
    async def load_bytes(self, *, storage_key: str) -> bytes:
        assert storage_key == "photo"
        return b"image-data"


def test_image_attachment_is_replayed_as_data_url() -> None:
    session = Session.create(title="Vision", owner_id=UUID(int=1))
    session.add_user_message(
        "What is in this image?",
        image_attachments=[
            ImageAttachment.restore(
                id=UUID(int=2),
                created_at=datetime.now(UTC),
                storage_key="photo",
                content_type="image/jpeg",
                file_name="photo.jpg",
                size_bytes=10,
            )
        ],
    )
    builder = AgentHistoryBuilder(cast(MessageAttachmentStore, _AttachmentStore()))

    result = asyncio.run(builder.build(session=session))[0]

    assert result.text == "What is in this image?"
    assert isinstance(result.content, tuple)
    assert isinstance(result.content[1], ImagePart)
    assert result.content[1].url == "data:image/jpeg;base64,aW1hZ2UtZGF0YQ=="
