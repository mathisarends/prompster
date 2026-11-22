from callm import ChatModel, SystemMessage, UserMessage

from backend.features.session.application.ports import (
    SessionTitleGenerator,
)


class LLMSessionTitleGenerator(SessionTitleGenerator):
    def __init__(self, llm: ChatModel) -> None:
        self._llm = llm

    async def generate(self, initial_prompt: str) -> str:
        response = await self._llm.call(
            [
                SystemMessage(
                    content=(
                        "Generate a short, concise title (max 5 words) for a session "
                        "based on the user's initial prompt. Respond with only the title, no punctuation."
                    )
                ),
                UserMessage(content=initial_prompt),
            ]
        )
        return response.completion
