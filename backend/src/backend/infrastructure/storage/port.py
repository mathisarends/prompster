from abc import ABC, abstractmethod

from backend.infrastructure.storage.views import (
    ContentType,
    StorageFile,
    UploadResponse,
)


class StorageBackend(ABC):
    @abstractmethod
    async def upload_bytes(
        self, path: str, data: bytes, content_type: ContentType | None = None
    ) -> UploadResponse:
        pass

    @abstractmethod
    async def delete_file(self, path: str) -> None:
        pass

    @abstractmethod
    async def delete_folder(self, path: str) -> None:
        pass

    @abstractmethod
    async def list_files(self, path: str = "") -> list[StorageFile]:
        pass

    @abstractmethod
    async def get_signed_url(self, path: str, ttl_seconds: int = 3600) -> str:
        pass

    @abstractmethod
    async def exists(self, path: str) -> bool:
        pass
