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
        self.moved: list[tuple[str, str]] = []
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

    async def move(self, source_path: str, destination_path: str) -> None:
        self.moved.append((source_path, destination_path))

    async def list_files(self, path: str = ""):
        class _StorageFile:
            def __init__(self, name: str) -> None:
                self.name = name

        return [_StorageFile(name=name) for name in self.files_by_prefix.get(path, [])]

    async def create_signed_url(self, path: str, ttl_seconds: int = 3600) -> str:
        return f"https://example.com/{path}?ttl={ttl_seconds}"

    async def exists(self, path: str) -> bool:
        return True


def test_save_stashed_image_attachment_builds_expected_storage_key() -> None:
    backend = _StorageBackendStub()
    store = StorageMessageAttachmentStore(storage_backend=backend)

    user_id = uuid4()
    attachment_id = uuid4()

    stored = asyncio.run(
        store.save_stashed_image_attachment(
            user_id=user_id,
            attachment_id=attachment_id,
            file_name="screenshot.png",
            content_type="image/png",
            content=b"1234",
        )
    )

    expected_key = f"users/{user_id}/stash/{attachment_id}.png"
    assert stored.storage_key == expected_key
    assert stored.content_type == "image/png"
    assert stored.file_name == "screenshot.png"
    assert stored.size_bytes == 4
    assert backend.uploaded == [(expected_key, b"1234", "image/png")]


def test_promote_stashed_image_attachment_moves_into_chat_folder() -> None:
    backend = _StorageBackendStub()
    store = StorageMessageAttachmentStore(storage_backend=backend)

    user_id = uuid4()
    session_id = uuid4()
    attachment_id = uuid4()
    stash_key = f"users/{user_id}/stash/{attachment_id}.png"

    destination_key = asyncio.run(
        store.promote_stashed_image_attachment(
            user_id=user_id,
            session_id=session_id,
            stash_storage_key=stash_key,
        )
    )

    expected_key = f"users/{user_id}/chat/{session_id}/{attachment_id}.png"
    assert destination_key == expected_key
    assert backend.moved == [(stash_key, expected_key)]


def test_delete_session_attachments_deletes_chat_prefix() -> None:
    backend = _StorageBackendStub()
    store = StorageMessageAttachmentStore(storage_backend=backend)
    user_id = uuid4()
    session_id = uuid4()

    asyncio.run(
        store.delete_session_attachments(user_id=user_id, session_id=session_id)
    )

    assert backend.deleted_prefixes == [f"users/{user_id}/chat/{session_id}/"]


def test_delete_user_attachments_deletes_user_prefix() -> None:
    backend = _StorageBackendStub()
    store = StorageMessageAttachmentStore(storage_backend=backend)
    user_id = uuid4()

    asyncio.run(store.delete_user_attachments(user_id=user_id))

    assert backend.deleted_prefixes == [f"users/{user_id}/"]
