from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class StoredAttachment:
    storage_key: str
    content_type: str
    file_name: str
    size_bytes: int


class MessageAttachmentStore(ABC):
    @abstractmethod
    async def save_image_attachment(
        self,
        *,
        session_id: UUID,
        message_id: UUID,
        attachment_id: UUID,
        file_name: str,
        content_type: str,
        content: bytes,
    ) -> StoredAttachment:
        pass

    @abstractmethod
    async def save_uploaded_image_attachment(
        self,
        *,
        session_id: UUID,
        attachment_id: UUID,
        file_name: str,
        content_type: str,
        content: bytes,
    ) -> StoredAttachment:
        pass

    @abstractmethod
    async def exists(self, *, storage_key: str) -> bool:
        pass

    @abstractmethod
    async def load_bytes(self, *, storage_key: str) -> bytes:
        pass

    @abstractmethod
    async def create_signed_url(
        self,
        *,
        storage_key: str,
        expires_in_seconds: int,
    ) -> str:
        pass

    @abstractmethod
    async def delete_session_attachments(self, *, session_id: UUID) -> None:
        pass

    @abstractmethod
    async def delete_unreferenced_uploaded_image_attachments(
        self,
        *,
        session_id: UUID,
        referenced_storage_keys: set[str],
    ) -> None:
        pass
