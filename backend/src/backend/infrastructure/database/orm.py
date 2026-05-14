from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel, text


class DatabaseEntity(SQLModel):
    id: UUID | None = Field(
        default=None,
        primary_key=True,
        sa_column_kwargs={"server_default": text("gen_random_uuid()")},
    )
    created_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"server_default": text("now()")},
    )
