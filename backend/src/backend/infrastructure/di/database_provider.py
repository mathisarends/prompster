from collections.abc import AsyncGenerator

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.infrastructure.database.settings import DatabaseSettings


class DatabaseProvider(Provider):
    scope = Scope.APP

    @provide(scope=Scope.APP)
    def database_config(self) -> DatabaseSettings:
        return DatabaseSettings()

    @provide(scope=Scope.APP)
    async def engine(
        self, config: DatabaseSettings
    ) -> AsyncGenerator[AsyncEngine, None]:
        engine = create_async_engine(
            config.db_uri,
            echo=False,
            pool_size=config.db_pool_size,
            max_overflow=config.db_max_overflow,
            pool_pre_ping=config.db_pool_pre_ping,
            pool_recycle=config.db_pool_recycle,
        )
        try:
            yield engine
        finally:
            await engine.dispose()

    @provide(scope=Scope.APP)
    def session_factory(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(engine, expire_on_commit=False)

    @provide(scope=Scope.REQUEST)
    async def session(
        self, factory: async_sessionmaker[AsyncSession]
    ) -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    @provide(scope=Scope.SESSION)
    async def websocket_session(
        self, factory: async_sessionmaker[AsyncSession]
    ) -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            async with session.begin():
                yield session
