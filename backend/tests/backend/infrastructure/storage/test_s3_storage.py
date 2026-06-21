import asyncio
from urllib.parse import parse_qs, urlparse

from backend.infrastructure.storage.impl.s3 import (
    S3StorageBackend,
    S3StorageCredentials,
)


def test_create_signed_url_signs_with_public_endpoint() -> None:
    backend = S3StorageBackend(
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
