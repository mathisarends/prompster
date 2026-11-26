import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as OrmSession
from sqlmodel import SQLModel

from backend.features.session.infrastructure.session_summary_query import (
    SqlSessionSummaryQuery,
)
from backend.platform.database.orm import (
    PlaylistTrackModel,
    SessionModel,
    SessionPlaylistModel,
    UserModel,
)

_NOW = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)
_OWNER_ID = UUID(int=1)


class _AsyncAdapter:
    """Runs the query's statements on a synchronous in-memory SQLite session."""

    def __init__(self, session: OrmSession) -> None:
        self._session = session

    async def execute(self, stmt: Any) -> Any:
        return self._session.execute(stmt)


@pytest.fixture
def orm() -> OrmSession:
    engine = create_engine("sqlite://")
    tables = [UserModel, SessionModel, SessionPlaylistModel, PlaylistTrackModel]
    # SQLModel adds __table__ to concrete mapped classes.
    table_objects = [model.__table__ for model in tables]  # type: ignore[attr-defined]
    SQLModel.metadata.create_all(engine, tables=table_objects)
    session = OrmSession(engine)
    session.add(UserModel(id=_OWNER_ID, name="Mathi", created_at=_NOW))
    session.commit()
    return session


def _deck(orm: OrmSession, *, number: int, covers: list[str | None]) -> UUID:
    deck_id = UUID(int=100 + number)
    orm.add(
        SessionModel(
            id=deck_id,
            title=f"Deck {number}",
            owner_id=_OWNER_ID,
            is_starred=False,
            created_at=_NOW,
            last_activity_at=_NOW + timedelta(minutes=number),
        )
    )
    if covers:
        playlist_id = UUID(int=200 + number)
        orm.add(
            SessionPlaylistModel(id=playlist_id, session_id=deck_id, created_at=_NOW)
        )
        for position, cover in enumerate(covers):
            orm.add(
                PlaylistTrackModel(
                    id=UUID(int=1000 + number * 10 + position),
                    playlist_id=playlist_id,
                    position=position,
                    title=f"Song {position}",
                    artist="Artist",
                    year=1990,
                    cover_url=cover,
                    created_at=_NOW,
                )
            )
    orm.commit()
    return deck_id


def test_summaries_collect_up_to_four_distinct_covers_in_playlist_order(
    orm: OrmSession,
) -> None:
    covers = [None, "https://img/1", "https://img/1", "https://img/2"]
    covers += ["https://img/3", "https://img/4", "https://img/5"]
    mosaic = _deck(orm, number=1, covers=covers)
    single = _deck(orm, number=2, covers=["https://img/9"])
    empty = _deck(orm, number=3, covers=[])
    # The in-memory SQLite adapter implements async execute for this query.
    query = SqlSessionSummaryQuery(_AsyncAdapter(orm))  # type: ignore[arg-type]

    summaries = asyncio.run(
        query.list_for_owner(owner_id=_OWNER_ID, limit=10, offset=0)
    )

    assert {summary.id: summary.cover_urls for summary in summaries} == {
        mosaic: ("https://img/1", "https://img/2", "https://img/3", "https://img/4"),
        single: ("https://img/9",),
        empty: (),
    }
