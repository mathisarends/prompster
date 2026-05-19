from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from backend.features.session.domain import Session


class SessionRunner(ABC):
    @abstractmethod
    def run(self, *, session: Session) -> AsyncIterator[str]:
        """Runs the LLM with the session context and yields text chunks."""
