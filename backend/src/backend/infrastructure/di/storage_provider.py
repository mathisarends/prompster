from backend.infrastructure.storage import (
    S3StorageBackend,
    StorageSettings,
    S3StorageCredentials,
    StorageBackend,
)
from dishka import Provider, Scope, provide


class StorageBackendProvider(Provider):
    @provide(scope=Scope.APP)
    def storage_config(self) -> StorageSettings:
        return StorageSettings()

    @provide(scope=Scope.APP)
    def storage_backend(self, config: StorageSettings) -> StorageBackend:
        return S3StorageBackend(S3StorageCredentials(), config.storage_bucket_name)
