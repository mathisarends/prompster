from abc import ABC, abstractmethod
from enum import StrEnum

from pydantic import BaseModel


class StorageFile(BaseModel):
    name: str


class ContentType(StrEnum):
    PNG = "image/png"
    MP4 = "video/mp4"
    TEST_PLAIN = "text/plain"


class UploadResponse(BaseModel):
    storage_path: str


class ObjectStorage(ABC):
    @abstractmethod
    async def upload_bytes(
        self, path: str, data: bytes, content_type: str | None = None
    ) -> UploadResponse:
        pass

    @abstractmethod
    async def download_bytes(self, path: str) -> bytes:
        pass

    @abstractmethod
    async def delete(self, path: str) -> None:
        pass

    @abstractmethod
    async def delete_folder(self, path: str) -> None:
        pass

    @abstractmethod
    async def move(self, source_path: str, destination_path: str) -> None:
        pass

    @abstractmethod
    async def list_files(self, path: str = "") -> list[StorageFile]:
        pass

    @abstractmethod
    async def create_signed_url(self, path: str, ttl_seconds: int = 3600) -> str:
        pass

    @abstractmethod
    async def exists(self, path: str) -> bool:
        pass

    async def delete_file(self, path: str) -> None:
        await self.delete(path)

    async def get_signed_url(self, path: str, ttl_seconds: int = 3600) -> str:
        return await self.create_signed_url(path=path, ttl_seconds=ttl_seconds)
