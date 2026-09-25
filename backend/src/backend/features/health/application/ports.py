from abc import ABC, abstractmethod


class ReadinessCheck(ABC):
    @abstractmethod
    async def check(self) -> None:
        """Raise ServiceNotReadyException when the service cannot take traffic."""
