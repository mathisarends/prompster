from backend.infrastructure.database.orm import DatabaseEntity
from sqlmodel import Field


class UserEntity(DatabaseEntity, table=True):
    __tablename__ = "users"

    name: str
    email: str = Field(index=True, unique=True)
    google_subject: str = Field(index=True, unique=True)
