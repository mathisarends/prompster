import asyncio
from types import SimpleNamespace
from typing import cast

from callm import ImageUrl

from backend.features.session.application.ports import MessageAttachmentStore
from backend.features.session.domain import UserMessage
from backend.features.session.infrastructure.agent_history import AgentHistoryBuilder


class _AttachmentStore:
    async def load_bytes(self, *, storage_key: str) -> bytes:
        assert storage_key == "photo"
        return b"image-data"


def test_image_attachment_is_replayed_as_callm_data_url() -> None:
    message = SimpleNamespace(
        content="What is in this image?",
        attachments=[],
        user_curation_events=[],
        image_attachments=[
            SimpleNamespace(storage_key="photo", content_type="image/jpeg")
        ],
    )
    builder = AgentHistoryBuilder(cast(MessageAttachmentStore, _AttachmentStore()))

    result = asyncio.run(builder._to_user_message(cast(UserMessage, message)))

    assert result.text == "What is in this image?"
    assert isinstance(result.content, tuple)
    assert isinstance(result.content[1], ImageUrl)
    assert result.content[1].url == "data:image/jpeg;base64,aW1hZ2UtZGF0YQ=="
