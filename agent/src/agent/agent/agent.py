import json
import logging
from pathlib import Path
from typing import Any, Self

from llmify import ChatModel

from agent.agent.messages.messages import MessageManager
from agent.agent.views import AgentResult, StepResult
from agent.events import (
    EventBus,
    RunCompletedEvent,
    RunStartedEvent,
    StepStartedEvent,
    ToolStatusEvent,
)
from agent.tools import Tools
from agent.tools.handler import Spotify

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (Path(__file__).parents[1] / "system_prompt.md").read_text(
    encoding="utf-8"
)


class Agent[Context]:
    def __init__(
        self,
        llm: ChatModel,
        tools: Tools | None = None,
        max_iterations: int = 10,
        context: Context | None = None,
        injectables: tuple[Any, ...] | list[Any] | None = None,
        system_prompt: str | None = None,
    ) -> None:
        self._llm = llm
        self._tools = tools or Tools()
        self._max_iterations = max_iterations
        self._context = context
        self._injectables = tuple(injectables or ())
        self._event_bus = EventBus()
        self._total_tokens = 0
        self._owns_spotify = False
        self._spotify = self._wire_tool_context()
        self._messages = MessageManager(system_prompt or _SYSTEM_PROMPT)
        self._tool_schema = self._tools.to_schema()

    def _wire_tool_context(self) -> Spotify:
        tool_context = self._tools.get_context()
        if self._context is not None:
            tool_context.provide(self._context)
        if self._injectables:
            tool_context.provide(*self._injectables)

        spotify = tool_context.resolve(Spotify)
        if spotify is None:
            spotify = Spotify()
            tool_context.provide(spotify)
            self._owns_spotify = True

        return spotify

    async def open(self) -> None:
        await self._spotify.open()

    async def close(self) -> None:
        if self._owns_spotify:
            await self._spotify.close()

    async def __aenter__(self) -> Self:
        await self.open()
        return self

    async def __aexit__(self, *_) -> None:
        await self.close()

    async def run(self, task: str) -> AgentResult:
        logger.info("Agent starting: %s", task[:120])
        await self.open()
        self._messages.add_user(task)
        self._total_tokens = 0

        await self._event_bus.dispatch(RunStartedEvent(message=task))

        for iteration in range(1, self._max_iterations + 1):
            await self._event_bus.dispatch(StepStartedEvent(step=iteration))
            result = await self.step()
            if result.done:
                final_result = AgentResult(
                    output=result.output,
                    finish_reason="done",
                    total_tokens=self._total_tokens,
                )
                await self._event_bus.dispatch(RunCompletedEvent(result=final_result))
                return final_result

        logger.warning("Max iterations (%d) reached", self._max_iterations)
        final_result = AgentResult(
            output="",
            finish_reason="max_iterations_reached",
            total_tokens=self._total_tokens,
        )
        await self._event_bus.dispatch(RunCompletedEvent(result=final_result))
        return final_result

    async def step(self) -> StepResult:
        response = await self._llm.invoke(self._messages.all(), tools=self._tool_schema)
        self._total_tokens += self._token_count(response.usage)

        if not response.tool_calls:
            output = self._stringify_completion(response.completion)
            self._messages.add_assistant(output)
            return StepResult(done=True, output=output)

        self._messages.add_assistant(
            self._stringify_completion(response.completion),
            tool_calls=response.tool_calls,
        )

        for call in response.tool_calls:
            args = self._parse_tool_args(call.function.arguments)
            status = self._tools.render_status(call.function.name, args)
            if status:
                await self._event_bus.dispatch(ToolStatusEvent(message=status))
            result = await self._tools.execute(call.function.name, args)
            self._messages.add_tool_result(
                tool_call_id=call.id,
                content=self._serialize_tool_result(result),
            )

        return StepResult(done=False)

    def reset(self) -> None:
        self._messages.reset()
        self._total_tokens = 0

    @staticmethod
    def _parse_tool_args(raw_arguments: str) -> dict[str, Any]:
        if not raw_arguments:
            return {}
        try:
            return json.loads(raw_arguments)
        except json.JSONDecodeError as error:
            logger.error("Failed to parse tool args JSON: %s", error)
            return {}

    @staticmethod
    def _serialize_tool_result(result: Any) -> str:
        if isinstance(result, str):
            return result
        if hasattr(result, "model_dump_json"):
            return result.model_dump_json()
        return json.dumps(result, ensure_ascii=False, default=str)

    @staticmethod
    def _stringify_completion(completion: Any) -> str:
        return completion if isinstance(completion, str) else str(completion or "")

    @staticmethod
    def _token_count(usage: Any) -> int:
        if usage is None:
            return 0
        total_tokens = getattr(usage, "total_tokens", None)
        if isinstance(total_tokens, int):
            return total_tokens
        prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
        completion_tokens = getattr(usage, "completion_tokens", 0) or 0
        return prompt_tokens + completion_tokens
