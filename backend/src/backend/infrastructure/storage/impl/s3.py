from contextlib import asynccontextmanager
from datetime import datetime
from typing import TYPE_CHECKING, AsyncIterator

import aioboto3
from backend.infrastructure.storage.port import StorageBackend
from backend.infrastructure.storage.views import (
    StorageFile,
    UploadResponse,
)
from botocore.config import Config
from botocore.exceptions import ClientError
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from types_aiobotocore_s3 import S3Client


class S3StorageCredentials(BaseSettings):
    endpoint_url: str
    access_key: str
    secret_key: str
    public_endpoint_url: str | None = None  # External URL for client access

    model_config = SettingsConfigDict(env_prefix="MINIO_")


class _S3Object(BaseModel):
    key: str = Field(alias="Key")
    last_modified: datetime = Field(alias="LastModified")
    size: int = Field(alias="Size")
    etag: str = Field(alias="ETag")
    storage_class: str | None = Field(default=None, alias="StorageClass")

    model_config = {"populate_by_name": True}

    @property
    def file_name(self) -> str:
        return self.key.split("/")[-1]

    def is_folder(self) -> bool:
        return self.key.endswith("/")


class _S3ListObjectsV2Response(BaseModel):
    contents: list[_S3Object] = Field(default_factory=list, alias="Contents")
    is_truncated: bool = Field(default=False, alias="IsTruncated")
    name: str | None = Field(default=None, alias="Name")
    prefix: str | None = Field(default=None, alias="Prefix")
    max_keys: int | None = Field(default=None, alias="MaxKeys")
    key_count: int | None = Field(default=None, alias="KeyCount")

    model_config = {"populate_by_name": True}


class _S3DeleteObject(BaseModel):
    key: str = Field(alias="Key")

    model_config = {"populate_by_name": True}


class _S3DeleteRequest(BaseModel):
    objects: list[_S3DeleteObject] = Field(alias="Objects")

    model_config = {"populate_by_name": True}


class _S3PresignedUrlParams(BaseModel):
    bucket: str = Field(alias="Bucket")
    key: str = Field(alias="Key")

    model_config = {"populate_by_name": True}


class _S3HeadObjectParams(BaseModel):
    bucket: str = Field(alias="Bucket")
    key: str = Field(alias="Key")

    model_config = {"populate_by_name": True}


_S3_CLIENT_CONFIG = Config(
    signature_version="s3v4",
    s3={"addressing_style": "path"},
)


class S3StorageBackend(StorageBackend):
    def __init__(
        self,
        credentials: S3StorageCredentials,
        bucket: str,
    ):
        self._session = aioboto3.Session()
        self._endpoint_url = credentials.endpoint_url
        self._public_endpoint_url = (
            credentials.public_endpoint_url or credentials.endpoint_url
        )
        self._access_key = credentials.access_key
        self._secret_key = credentials.secret_key
        self._bucket = bucket

    @asynccontextmanager
    async def _get_client(self) -> AsyncIterator[S3Client]:
        async with self._session.client(
            service_name="s3",
            endpoint_url=self._endpoint_url,
            region_name="us-east-1",
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
            config=_S3_CLIENT_CONFIG,
        ) as client:
            yield client

    async def upload_bytes(
        self, path: str, data: bytes, content_type: str | None = None
    ) -> UploadResponse:
        async with self._get_client() as s3:
            await s3.put_object(
                Bucket=self._bucket,
                Key=path,
                Body=data,
                ContentType=content_type,
            )

        return UploadResponse(storage_path=path)

    async def download_bytes(self, path: str) -> bytes:
        async with self._get_client() as s3:
            response = await s3.get_object(Bucket=self._bucket, Key=path)
            body = response["Body"]
            return await body.read()

    async def delete(self, path: str) -> None:
        async with self._get_client() as s3:
            await s3.delete_object(Bucket=self._bucket, Key=path)

    async def delete_folder(self, path: str) -> None:
        async with self._get_client() as s3:
            response = await s3.list_objects_v2(
                Bucket=self._bucket,
                Prefix=path,
            )

        s3_response = _S3ListObjectsV2Response.model_validate(response)
        objects_to_delete = [obj for obj in s3_response.contents if not obj.is_folder()]

        if not objects_to_delete:
            return

        delete_request = _S3DeleteRequest(
            objects=[_S3DeleteObject(key=obj.key) for obj in objects_to_delete]
        )

        async with self._get_client() as s3:
            await s3.delete_objects(
                Bucket=self._bucket,
                Delete=delete_request.model_dump(by_alias=True),
            )

    async def move(self, source_path: str, destination_path: str) -> None:
        async with self._get_client() as s3:
            await s3.copy_object(
                Bucket=self._bucket,
                CopySource={"Bucket": self._bucket, "Key": source_path},
                Key=destination_path,
            )
            await s3.delete_object(Bucket=self._bucket, Key=source_path)

    async def list_files(self, path: str = "") -> list[StorageFile]:
        async with self._get_client() as s3:
            response = await s3.list_objects_v2(
                Bucket=self._bucket,
                Prefix=path,
            )

        s3_response = _S3ListObjectsV2Response.model_validate(response)

        return [
            StorageFile(name=obj.file_name)
            for obj in s3_response.contents
            if not obj.is_folder()
        ]

    async def create_signed_url(self, path: str, ttl_seconds: int = 3600) -> str:
        params = _S3PresignedUrlParams(bucket=self._bucket, key=path)

        async with self._get_client() as s3:
            signed_url: str = await s3.generate_presigned_url(
                ClientMethod="get_object",
                Params=params.model_dump(by_alias=True),
                ExpiresIn=ttl_seconds,
            )

        # Replace internal endpoint with public endpoint for client access
        if self._endpoint_url != self._public_endpoint_url:
            signed_url = signed_url.replace(
                self._endpoint_url, self._public_endpoint_url
            )

        return signed_url

    async def exists(self, path: str) -> bool:
        params = _S3HeadObjectParams(bucket=self._bucket, key=path)

        async with self._get_client() as s3:
            try:
                await s3.head_object(**params.model_dump(by_alias=True))
                return True
            except ClientError as e:
                if e.response["Error"]["Code"] == "404":
                    return False
                raise
