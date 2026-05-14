from abc import ABC, abstractmethod


class SessionTitleGenerator(ABC):
    @abstractmethod
    async def generate(self, initial_prompt: str) -> str:
        """Generates a short title based on the initial prompt."""
