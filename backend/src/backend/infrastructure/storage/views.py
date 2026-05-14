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
