from dishka import Provider, Scope, provide

from backend.platform.storage import (
    ObjectStorage,
    S3ObjectStorage,
    S3StorageCredentials,
    StorageSettings,
)


class ObjectStorageProvider(Provider):
    @provide(scope=Scope.APP)
    def storage_config(self) -> StorageSettings:
        return StorageSettings()

    @provide(scope=Scope.APP)
    def object_storage(self, config: StorageSettings) -> ObjectStorage:
        credentials = S3StorageCredentials()
        return S3ObjectStorage(
            endpoint_url=credentials.endpoint_url,
            access_key=credentials.access_key,
            secret_key=credentials.secret_key,
            bucket=config.storage_bucket_name,
            public_endpoint_url=credentials.public_endpoint_url,
        )
