from dataclasses import dataclass
from uuid import UUID, uuid4

from backend.features.session.application.ports import MessageAttachmentStore

ALLOWED_IMAGE_CONTENT_TYPES = frozenset({"image/png", "image/jpeg", "image/webp"})
MAX_IMAGE_ATTACHMENT_SIZE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_ATTACHMENTS_PER_MESSAGE = 5


@dataclass(frozen=True)
class SessionImageAttachmentUpload:
    file_name: str
    content_type: str
    content: bytes


@dataclass(frozen=True)
class SessionImageAttachmentReference:
    id: UUID
    storage_key: str
    content_type: str
    file_name: str
    size_bytes: int


@dataclass(frozen=True)
class StashedImageAttachment:
    id: UUID
    storage_key: str
    content_type: str
    file_name: str
    size_bytes: int


def normalize_content_type(content_type: str) -> str:
    return content_type.split(";", 1)[0].strip().lower()


class ImageAttachmentService:
    """Handles loose image uploads that are not yet tied to a session.

    Uploads are stored in a per-user stash so screenshots can be attached even
    before a session exists. They are only moved into a session's chat folder
    when a message references them (see SessionConversationService).
    """

    def __init__(self, message_attachment_store: MessageAttachmentStore) -> None:
        self._message_attachment_store = message_attachment_store

    async def stash_image(
        self,
        *,
        user_id: UUID,
        image: SessionImageAttachmentUpload,
    ) -> StashedImageAttachment:
        content_type = normalize_content_type(image.content_type)
        self._validate_upload(content_type=content_type, image=image)
        attachment_id = uuid4()
        stored = await self._message_attachment_store.save_stashed_image_attachment(
            user_id=user_id,
            attachment_id=attachment_id,
            file_name=image.file_name,
            content_type=content_type,
            content=image.content,
        )
        return StashedImageAttachment(
            id=attachment_id,
            storage_key=stored.storage_key,
            content_type=stored.content_type,
            file_name=stored.file_name,
            size_bytes=stored.size_bytes,
        )

    def _validate_upload(
        self,
        *,
        content_type: str,
        image: SessionImageAttachmentUpload,
    ) -> None:
        if content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
            raise ValueError(f"Unsupported image content type: {content_type}.")
        if len(image.content) == 0:
            raise ValueError(f"Image '{image.file_name}' is empty.")
        if len(image.content) > MAX_IMAGE_ATTACHMENT_SIZE_BYTES:
            raise ValueError(
                f"Image '{image.file_name}' exceeds the maximum allowed size of "
                f"{MAX_IMAGE_ATTACHMENT_SIZE_BYTES // (1024 * 1024)} MB."
            )
