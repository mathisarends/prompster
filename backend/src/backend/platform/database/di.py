from pathlib import Path

from fastapi_canon.integrations.database import AlembicMigrations, Database, Tables

from backend.platform.database.orm import (
    ActiveSessionRunModel,
    AuthIdentityModel,
    OAuthConnectionModel,
    PlaylistTrackModel,
    SessionAgentCheckpointModel,
    SessionArtistReferenceModel,
    SessionAssistantMessageModel,
    SessionModel,
    SessionOnboardingQuestionModel,
    SessionPlaylistModel,
    SessionPlaylistReferenceModel,
    SessionToolCallModel,
    SessionToolCallSequenceModel,
    SessionUserCurationEventModel,
    SessionUserMessageAttachmentModel,
    SessionUserMessageImageAttachmentModel,
    SessionUserMessageModel,
    UserModel,
)
from backend.platform.database.settings import DatabaseSettings

DATABASE_TABLES = Tables(
    UserModel,
    AuthIdentityModel,
    OAuthConnectionModel,
    SessionModel,
    ActiveSessionRunModel,
    SessionAgentCheckpointModel,
    SessionUserMessageModel,
    SessionUserMessageAttachmentModel,
    SessionUserMessageImageAttachmentModel,
    SessionAssistantMessageModel,
    SessionUserCurationEventModel,
    SessionPlaylistReferenceModel,
    SessionArtistReferenceModel,
    SessionToolCallSequenceModel,
    SessionToolCallModel,
    SessionOnboardingQuestionModel,
    SessionPlaylistModel,
    PlaylistTrackModel,
)

_MIGRATIONS_DIRECTORY = Path(__file__).resolve().parents[4] / "migrations"


def create_database(settings: DatabaseSettings) -> Database:
    return Database(
        url=settings.db_uri,
        engine_options={
            "pool_size": settings.db_pool_size,
            "max_overflow": settings.db_max_overflow,
            "pool_pre_ping": settings.db_pool_pre_ping,
            "pool_recycle": settings.db_pool_recycle,
        },
        migrations=AlembicMigrations(directory=_MIGRATIONS_DIRECTORY),
    )
