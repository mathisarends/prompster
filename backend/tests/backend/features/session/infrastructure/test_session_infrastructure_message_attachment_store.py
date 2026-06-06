import asyncio
from uuid import uuid4

from backend.features.session.infrastructure.message_attachment_store import (
    StorageMessageAttachmentStore,
)
from backend.infrastructure.storage import StorageBackend


class _StorageBackendStub(StorageBackend):
    def __init__(self) -> None:
        self.uploaded: list[tuple[str, bytes, str | None]] = []
        self.deleted_prefixes: list[str] = []
        self.deleted_files: list[str] = []
        self.files_by_prefix: dict[str, list[str]] = {}

    async def upload_bytes(
        self, path: str, data: bytes, content_type: str | None = None
    ):
        self.uploaded.append((path, data, content_type))

        class _UploadResponse:
            storage_path = path

        return _UploadResponse()

    async def download_bytes(self, path: str) -> bytes:
        return b"raw-bytes"

    async def delete(self, path: str) -> None:
        self.deleted_files.append(path)

    async def delete_folder(self, path: str) -> None:
        self.deleted_prefixes.append(path)

    async def list_files(self, path: str = ""):
        class _StorageFile:
            def __init__(self, name: str) -> None:
                self.name = name

        return [_StorageFile(name=name) for name in self.files_by_prefix.get(path, [])]

    async def create_signed_url(self, path: str, ttl_seconds: int = 3600) -> str:
        return f"https://example.com/{path}?ttl={ttl_seconds}"

    async def exists(self, path: str) -> bool:
        return True


def test_save_image_attachment_builds_expected_storage_key() -> None:
    backend = _StorageBackendStub()
    store = StorageMessageAttachmentStore(storage_backend=backend)

    session_id = uuid4()
    message_id = uuid4()
    attachment_id = uuid4()

    stored = asyncio.run(
        store.save_image_attachment(
            session_id=session_id,
            message_id=message_id,
            attachment_id=attachment_id,
            file_name="screenshot.png",
            content_type="image/png",
            content=b"1234",
        )
    )

    expected_key = (
        f"sessions/{session_id}/messages/{message_id}/attachments/{attachment_id}.png"
    )
    assert stored.storage_key == expected_key
    assert stored.content_type == "image/png"
    assert stored.file_name == "screenshot.png"
    assert stored.size_bytes == 4
    assert backend.uploaded == [(expected_key, b"1234", "image/png")]


def test_save_uploaded_image_attachment_builds_expected_storage_key() -> None:
    backend = _StorageBackendStub()
    store = StorageMessageAttachmentStore(storage_backend=backend)

    session_id = uuid4()
    attachment_id = uuid4()

    stored = asyncio.run(
        store.save_uploaded_image_attachment(
            session_id=session_id,
            attachment_id=attachment_id,
            file_name="screenshot.png",
            content_type="image/png",
            content=b"1234",
        )
    )

    expected_key = f"sessions/{session_id}/uploads/{attachment_id}.png"
    assert stored.storage_key == expected_key
    assert stored.content_type == "image/png"
    assert stored.file_name == "screenshot.png"
    assert stored.size_bytes == 4
    assert backend.uploaded == [(expected_key, b"1234", "image/png")]


def test_delete_session_attachments_deletes_session_prefix() -> None:
    backend = _StorageBackendStub()
    store = StorageMessageAttachmentStore(storage_backend=backend)
    session_id = uuid4()

    asyncio.run(store.delete_session_attachments(session_id=session_id))

    assert backend.deleted_prefixes == [f"sessions/{session_id}/"]


def test_delete_unreferenced_uploaded_image_attachments_keeps_referenced_files() -> (
    None
):
    backend = _StorageBackendStub()
    store = StorageMessageAttachmentStore(storage_backend=backend)
    session_id = uuid4()
    kept_id = uuid4()
    deleted_id = uuid4()
    prefix = f"sessions/{session_id}/uploads/"
    kept_key = f"{prefix}{kept_id}.png"
    deleted_key = f"{prefix}{deleted_id}.png"
    backend.files_by_prefix[prefix] = [f"{kept_id}.png", f"{deleted_id}.png"]

    asyncio.run(
        store.delete_unreferenced_uploaded_image_attachments(
            session_id=session_id,
            referenced_storage_keys={kept_key},
        )
    )

    assert backend.deleted_files == [deleted_key]
