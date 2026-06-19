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
    async def save_stashed_image_attachment(
        self,
        *,
        user_id: UUID,
        attachment_id: UUID,
        file_name: str,
        content_type: str,
        content: bytes,
    ) -> StoredAttachment:
        """Persist a loose, not-yet-referenced image upload in the user's stash."""

    @abstractmethod
    async def promote_stashed_image_attachment(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        stash_storage_key: str,
    ) -> str:
        """Move a stashed image into the chat folder and return its new key."""

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
    async def delete_session_attachments(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
    ) -> None:
        pass

    @abstractmethod
    async def delete_user_attachments(self, *, user_id: UUID) -> None:
        pass
