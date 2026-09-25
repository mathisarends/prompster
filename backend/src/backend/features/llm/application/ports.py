from abc import ABC, abstractmethod

from llm import ChatModel

from backend.features.llm.domain import LLMModelInfo


class ChatModelFactory(ABC):
    @abstractmethod
    def create(self, model: LLMModelInfo) -> ChatModel: ...
