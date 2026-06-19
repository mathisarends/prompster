from abc import ABC, abstractmethod
from uuid import UUID


class ActiveSessionRunStore(ABC):
    @abstractmethod
    async def register(self, *, session_id: UUID, run_id: UUID) -> None:
        """Registers the currently active run for a session."""

    @abstractmethod
    async def complete(self, *, session_id: UUID, run_id: UUID) -> None:
        """Removes the active run if it still matches the given run id."""

    @abstractmethod
    async def request_stop(self, *, session_id: UUID) -> bool:
        """Persists a stop request for the active session run."""

    @abstractmethod
    async def is_stop_requested(self, *, session_id: UUID, run_id: UUID) -> bool:
        """Returns whether the active run has a persisted stop request."""
