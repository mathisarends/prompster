from pathlib import PurePosixPath
from uuid import UUID

from backend.features.session.application.ports import (
    MessageAttachmentStore,
    StoredAttachment,
)
from backend.infrastructure.storage import ObjectStorage


class StorageMessageAttachmentStore(MessageAttachmentStore):
    def __init__(self, storage_backend: ObjectStorage) -> None:
        self._storage_backend = storage_backend

    async def save_stashed_image_attachment(
        self,
        *,
        user_id: UUID,
        attachment_id: UUID,
        file_name: str,
        content_type: str,
        content: bytes,
    ) -> StoredAttachment:
        ext = _resolve_extension(file_name=file_name, content_type=content_type)
        storage_key = f"users/{user_id}/stash/{attachment_id}.{ext}"
        normalized_file_name = file_name.strip() or f"attachment.{ext}"
        await self._storage_backend.upload_bytes(
            path=storage_key,
            data=content,
            content_type=content_type,
        )
        return StoredAttachment(
            storage_key=storage_key,
            content_type=content_type,
            file_name=normalized_file_name,
            size_bytes=len(content),
        )

    async def promote_stashed_image_attachment(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        stash_storage_key: str,
    ) -> str:
        file_name = PurePosixPath(stash_storage_key).name
        destination_key = f"users/{user_id}/chat/{session_id}/{file_name}"
        await self._storage_backend.move(stash_storage_key, destination_key)
        return destination_key

    async def exists(self, *, storage_key: str) -> bool:
        return await self._storage_backend.exists(path=storage_key)

    async def load_bytes(self, *, storage_key: str) -> bytes:
        return await self._storage_backend.download_bytes(path=storage_key)

    async def create_signed_url(
        self,
        *,
        storage_key: str,
        expires_in_seconds: int,
    ) -> str:
        return await self._storage_backend.create_signed_url(
            path=storage_key,
            ttl_seconds=expires_in_seconds,
        )

    async def delete_session_attachments(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
    ) -> None:
        await self._storage_backend.delete_folder(
            path=f"users/{user_id}/chat/{session_id}/"
        )

    async def delete_user_attachments(self, *, user_id: UUID) -> None:
        await self._storage_backend.delete_folder(path=f"users/{user_id}/")


_CONTENT_TYPE_TO_EXTENSION = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
}


def _resolve_extension(*, file_name: str, content_type: str) -> str:
    inferred = _CONTENT_TYPE_TO_EXTENSION.get(content_type.lower())
    if inferred is not None:
        return inferred
    suffix = PurePosixPath(file_name).suffix.strip().lstrip(".").lower()
    if suffix:
        return "".join(ch for ch in suffix if ch.isalnum()) or "bin"
    return "bin"
