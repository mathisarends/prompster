from datetime import timedelta

from obstore import sign_async
from obstore.store import S3Store

from backend.shared.storage import ObjectStorage, StorageFile, UploadResponse


class S3ObjectStorage(ObjectStorage):
    def __init__(
        self,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        public_endpoint_url: str | None = None,
    ) -> None:
        self._store = S3Store(
            bucket=bucket,
            endpoint=endpoint_url,
            access_key_id=access_key,
            secret_access_key=secret_key,
            region="us-east-1",
            virtual_hosted_style_request=False,
            client_options={"allow_http": True},
        )
        self._public_store = (
            S3Store(
                bucket=bucket,
                endpoint=public_endpoint_url,
                access_key_id=access_key,
                secret_access_key=secret_key,
                region="us-east-1",
                virtual_hosted_style_request=False,
                client_options={"allow_http": True},
            )
            if public_endpoint_url
            else self._store
        )

    async def upload_bytes(
        self, path: str, data: bytes, content_type: str | None = None
    ) -> UploadResponse:
        attributes = {"Content-Type": content_type} if content_type else None
        await self._store.put_async(path, data, attributes=attributes)
        return UploadResponse(storage_path=path)

    async def download_bytes(self, path: str) -> bytes:
        response = await self._store.get_async(path)
        return bytes(await response.bytes_async())

    async def delete(self, path: str) -> None:
        await self._store.delete_async(path)

    async def delete_folder(self, path: str) -> None:
        objects = await self._store.list_async(path).collect_async()
        if objects:
            await self._store.delete_async([obj["path"] for obj in objects])

    async def move(self, source_path: str, destination_path: str) -> None:
        await self._store.rename_async(source_path, destination_path)

    async def list_files(self, path: str = "") -> list[StorageFile]:
        objects = await self._store.list_async(path).collect_async()
        return [StorageFile(name=obj["path"].rsplit("/", 1)[-1]) for obj in objects]

    async def create_signed_url(self, path: str, ttl_seconds: int = 3600) -> str:
        return await sign_async(
            self._public_store, "GET", path, timedelta(seconds=ttl_seconds)
        )

    async def exists(self, path: str) -> bool:
        try:
            await self._store.head_async(path)
            return True
        except FileNotFoundError:
            return False
