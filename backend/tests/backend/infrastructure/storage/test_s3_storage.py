import asyncio
from urllib.parse import parse_qs, urlparse

from backend.infrastructure.storage.impl.s3 import (
    S3ObjectStorage,
    S3StorageCredentials,
)
from obstore.store import MemoryStore


def test_object_operations() -> None:
    async def run() -> None:
        storage = S3ObjectStorage.__new__(S3ObjectStorage)
        storage._store = MemoryStore()
        storage._public_store = storage._store

        await storage.upload_bytes("folder/file.txt", b"hello", "text/plain")
        assert await storage.exists("folder/file.txt")
        assert await storage.download_bytes("folder/file.txt") == b"hello"
        files = await storage.list_files("folder/")
        assert [file.name for file in files] == ["file.txt"]

        await storage.move("folder/file.txt", "folder/moved.txt")
        assert not await storage.exists("folder/file.txt")
        await storage.delete_folder("folder/")
        assert not await storage.exists("folder/moved.txt")

    asyncio.run(run())


def test_create_signed_url_signs_with_public_endpoint() -> None:
    backend = S3ObjectStorage(
        credentials=S3StorageCredentials(
            endpoint_url="http://minio:9000",
            public_endpoint_url="http://127.0.0.1:9000",
            access_key="minioadmin",
            secret_key="minioadmin",
        ),
        bucket="prompster",
    )

    signed_url = asyncio.run(
        backend.create_signed_url(
            path="users/u/chat/s/image.png",
            ttl_seconds=86_400,
        )
    )

    parsed = urlparse(signed_url)
    query = parse_qs(parsed.query)

    assert parsed.scheme == "http"
    assert parsed.netloc == "127.0.0.1:9000"
    assert parsed.path == "/prompster/users/u/chat/s/image.png"
    assert query["X-Amz-Expires"] == ["86400"]
    assert "X-Amz-Signature" in query
