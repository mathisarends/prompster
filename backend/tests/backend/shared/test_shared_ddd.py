from datetime import datetime, timezone
from uuid import uuid4

from backend.shared.ddd import Aggregate, Entity


class TestSharedDddEntity:
    def test_entity_keeps_id_and_created_at(self) -> None:
        entity_id = uuid4()
        created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

        entity = Entity(id=entity_id, created_at=created_at)

        assert entity.id == entity_id
        assert entity.created_at == created_at

    def test_entities_with_same_id_are_equal(self) -> None:
        entity_id = uuid4()
        created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

        first = Entity(id=entity_id, created_at=created_at)
        second = Entity(id=entity_id, created_at=created_at)

        assert first == second
        assert hash(first) == hash(second)

    def test_entities_with_different_ids_are_not_equal(self) -> None:
        created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

        assert Entity(id=uuid4(), created_at=created_at) != Entity(
            id=uuid4(), created_at=created_at
        )

    def test_entities_of_different_types_are_not_equal(self) -> None:
        entity_id = uuid4()
        created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

        assert Entity(id=entity_id, created_at=created_at) != Aggregate(
            id=entity_id, created_at=created_at
        )


class TestSharedDddAggregate:
    def test_aggregate_is_entity(self) -> None:
        assert issubclass(Aggregate, Entity)
