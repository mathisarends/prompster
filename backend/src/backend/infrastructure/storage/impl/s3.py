# from contextlib import asynccontextmanager
# from datetime import datetime
# from enum import StrEnum
# from typing import TYPE_CHECKING, AsyncIterator

# try:
#     import aioboto3
#     from botocore.exceptions import ClientError
# except ImportError as e:
#     raise ImportError(
#         "S3 dependencies are not installed. Install them with: uv add storage[s3]"
#     ) from e

# from pydantic import BaseModel, Field
# from pydantic_settings import SettingsConfigDict

# from storage.adapters.port import StorageBackend
# from storage.credentials import BaseCredentials
# from storage.views import (
#     ContentType,
#     StorageFile,
#     UploadResponse,
# )

# if TYPE_CHECKING:
#     from types_aiobotocore_s3 import S3Client


# class S3StorageCredentials(BaseCredentials):
#     endpoint_url: str
#     access_key: str
#     secret_key: str
#     public_endpoint_url: str | None = None  # External URL for client access

#     model_config = SettingsConfigDict(env_prefix="MINIO_")


# class S3Service(StrEnum):
#     S3 = "s3"


# class S3Operation(StrEnum):
#     GET_OBJECT = "get_object"
#     PUT_OBJECT = "put_object"
#     DELETE_OBJECT = "delete_object"
#     HEAD_OBJECT = "head_object"
#     LIST_OBJECTS_V2 = "list_objects_v2"


# class S3Object(BaseModel):
#     key: str = Field(alias="Key")
#     last_modified: datetime = Field(alias="LastModified")
#     size: int = Field(alias="Size")
#     etag: str = Field(alias="ETag")
#     storage_class: str | None = Field(default=None, alias="StorageClass")

#     model_config = {"populate_by_name": True}

#     @property
#     def file_name(self) -> str:
#         return self.key.split("/")[-1]

#     def is_folder(self) -> bool:
#         return self.key.endswith("/")


# class S3ListObjectsV2Response(BaseModel):
#     contents: list[S3Object] = Field(default_factory=list, alias="Contents")
#     is_truncated: bool = Field(default=False, alias="IsTruncated")
#     name: str | None = Field(default=None, alias="Name")
#     prefix: str | None = Field(default=None, alias="Prefix")
#     max_keys: int | None = Field(default=None, alias="MaxKeys")
#     key_count: int | None = Field(default=None, alias="KeyCount")

#     model_config = {"populate_by_name": True}


# class S3DeleteObject(BaseModel):
#     key: str = Field(alias="Key")

#     model_config = {"populate_by_name": True}


# class S3DeleteRequest(BaseModel):
#     objects: list[S3DeleteObject] = Field(alias="Objects")

#     model_config = {"populate_by_name": True}


# class S3PresignedUrlParams(BaseModel):
#     bucket: str = Field(alias="Bucket")
#     key: str = Field(alias="Key")

#     model_config = {"populate_by_name": True}


# class S3HeadObjectParams(BaseModel):
#     bucket: str = Field(alias="Bucket")
#     key: str = Field(alias="Key")

#     model_config = {"populate_by_name": True}


# class S3StorageBackend(StorageBackend):
#     def __init__(
#         self,
#         credentials: S3StorageCredentials,
#         bucket: str,
#     ):
#         self._session = aioboto3.Session()
#         self._endpoint_url = credentials.endpoint_url
#         self._public_endpoint_url = (
#             credentials.public_endpoint_url or credentials.endpoint_url
#         )
#         self._access_key = credentials.access_key
#         self._secret_key = credentials.secret_key
#         self._bucket = bucket

#     @asynccontextmanager
#     async def _get_client(self) -> AsyncIterator[S3Client]:
#         async with self._session.client(
#             S3Service.S3,
#             endpoint_url=self._endpoint_url,
#             aws_access_key_id=self._access_key,
#             aws_secret_access_key=self._secret_key,
#         ) as client:
#             yield client

#     async def upload_bytes(
#         self, path: str, data: bytes, content_type: ContentType | None = None
#     ) -> UploadResponse:
#         async with self._get_client() as s3:
#             await s3.put_object(
#                 Bucket=self._bucket,
#                 Key=path,
#                 Body=data,
#                 ContentType=content_type,
#             )

#         return UploadResponse(storage_path=path)

#     async def delete_file(self, path: str) -> None:
#         async with self._get_client() as s3:
#             await s3.delete_object(Bucket=self._bucket, Key=path)

#     async def delete_folder(self, path: str) -> None:
#         async with self._get_client() as s3:
#             response = await s3.list_objects_v2(
#                 Bucket=self._bucket,
#                 Prefix=path,
#             )

#         s3_response = S3ListObjectsV2Response.model_validate(response)
#         objects_to_delete = [obj for obj in s3_response.contents if not obj.is_folder()]

#         if not objects_to_delete:
#             return

#         delete_request = S3DeleteRequest(
#             objects=[S3DeleteObject(key=obj.key) for obj in objects_to_delete]
#         )

#         async with self._get_client() as s3:
#             await s3.delete_objects(
#                 Bucket=self._bucket,
#                 Delete=delete_request.model_dump(by_alias=True),
#             )

#     async def list_files(self, path: str = "") -> list[StorageFile]:
#         async with self._get_client() as s3:
#             response = await s3.list_objects_v2(
#                 Bucket=self._bucket,
#                 Prefix=path,
#             )

#         s3_response = S3ListObjectsV2Response.model_validate(response)

#         return [
#             StorageFile(name=obj.file_name)
#             for obj in s3_response.contents
#             if not obj.is_folder()
#         ]

#     async def get_signed_url(self, path: str, ttl_seconds: int = 3600) -> str:
#         params = S3PresignedUrlParams(bucket=self._bucket, key=path)

#         async with self._get_client() as s3:
#             signed_url: str = await s3.generate_presigned_url(
#                 S3Operation.GET_OBJECT,
#                 Params=params.model_dump(by_alias=True),
#                 ExpiresIn=ttl_seconds,
#             )

#         # Replace internal endpoint with public endpoint for client access
#         if self._endpoint_url != self._public_endpoint_url:
#             signed_url = signed_url.replace(
#                 self._endpoint_url, self._public_endpoint_url
#             )

#         return signed_url

#     async def exists(self, path: str) -> bool:
#         params = S3HeadObjectParams(bucket=self._bucket, key=path)

#         async with self._get_client() as s3:
#             try:
#                 await s3.head_object(**params.model_dump(by_alias=True))
#                 return True
#             except ClientError as e:
#                 if e.response["Error"]["Code"] == "404":
#                     return False
#                 raise
