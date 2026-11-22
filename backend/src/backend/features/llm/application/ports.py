from abc import ABC, abstractmethod

from pydantic_ai.models import Model

from backend.features.llm.domain import LLMModelInfo


class ChatModels(ABC):
    """Owns one chat model client per configured model for the app's lifetime."""

    @abstractmethod
    def get(self, model: LLMModelInfo) -> Model: ...

    @abstractmethod
    async def aclose(self) -> None: ...
