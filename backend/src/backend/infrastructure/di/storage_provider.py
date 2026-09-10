from dishka import Provider, Scope, provide

from backend.infrastructure.storage import (
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
        return S3ObjectStorage(S3StorageCredentials(), config.storage_bucket_name)
