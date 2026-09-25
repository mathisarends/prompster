from datetime import datetime
from uuid import UUID


class Entity:
    def __init__(self, *, id: UUID, created_at: datetime) -> None:
        self._id = id
        self.created_at = created_at

    @property
    def id(self) -> UUID:
        return self._id

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return False
        return type(self) is type(other) and self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)


class Aggregate(Entity):
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id}, created_at={self.created_at})"
