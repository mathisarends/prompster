from pydantic_ai import Agent
from pydantic_ai.models import Model

from backend.features.session.application.ports import (
    SessionTitleGenerator,
)

_INSTRUCTIONS = (
    "Generate a short, concise title (max 5 words) for a session "
    "based on the user's initial prompt. Respond with only the title, no punctuation."
)


class LLMSessionTitleGenerator(SessionTitleGenerator):
    def __init__(self, llm: Model) -> None:
        self._llm = llm
        self._agent = Agent(llm, instructions=_INSTRUCTIONS)

    async def generate(self, initial_prompt: str) -> str:
        # Holding the model context keeps its shared client open during this call.
        async with self._llm:
            result = await self._agent.run(initial_prompt)
        return result.output
