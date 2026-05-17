from datetime import datetime, timezone
from uuid import UUID, uuid4

from backend.shared.ddd import Aggregate, Entity


class TestSharedDddEntity:
    def test_entity_keeps_explicit_id_and_created_time(self) -> None:
        entity_id = uuid4()
        created_time = datetime(2026, 1, 1, tzinfo=timezone.utc)

        entity = Entity(id=entity_id, created_time=created_time)

        assert entity.id == entity_id
        assert entity.created_at == created_time

    def test_entity_generates_uuid_and_utc_created_at_by_default(self) -> None:
        before = datetime.now(timezone.utc)
        entity = Entity()
        after = datetime.now(timezone.utc)

        assert isinstance(entity.id, UUID)
        assert entity.created_at.tzinfo is not None
        assert entity.created_at.utcoffset() == timezone.utc.utcoffset(None)
        assert before <= entity.created_at <= after


class TestSharedDddAggregate:
    def test_aggregate_is_entity_alias(self) -> None:
        assert Aggregate is Entity
