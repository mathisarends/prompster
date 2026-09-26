from abc import ABC, abstractmethod

from callm import ChatModel

from backend.features.llm.domain import LLMModelInfo


class ChatModels(ABC):
    """Owns one chat model client per configured model for the app's lifetime."""

    @abstractmethod
    def get(self, model: LLMModelInfo) -> ChatModel: ...

    @abstractmethod
    async def aclose(self) -> None: ...
