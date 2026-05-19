import logging
from collections.abc import AsyncGenerator
from pathlib import Path

from llmify import ChatModel

from agent.agent.events import (
    AgentEvent,
    AssistantMessageEvent,
    RunCompletedEvent,
    RunStartedEvent,
    StepStartedEvent,
    ToolCallEvent,
    ToolResultEvent,
    WorkspaceUpdatedEvent,
)
from agent.agent.messages.messages import MessageManager
from agent.tools import Tools
from agent.tools.handler import Spotify
from agent.workspace import WorkspaceStore

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (Path(__file__).parents[1] / "system_prompt.md").read_text(
    encoding="utf-8"
)


class Agent:
    def __init__(
        self,
        llm: ChatModel,
        tools: Tools | None = None,
        messages: MessageManager | None = None,
        max_iterations: int = 10,
        system_prompt: str | None = None,
    ) -> None:
        self._llm = llm
        self._tools = tools or Tools()
        self._max_iterations = max_iterations
        self._messages = messages or MessageManager(system_prompt or _SYSTEM_PROMPT)
        self._spotify, self._owns_spotify = self._wire_spotify_context()
        self._workspace_store = self._wire_workspace_context()
        self._tool_schema = self._tools.to_schema()

    def _wire_spotify_context(self) -> tuple[Spotify, bool]:
        tool_context = self._tools.get_context()
        spotify = tool_context.resolve(Spotify)
        if spotify is None:
            spotify = Spotify()
            tool_context.provide(spotify)
            return spotify, True
        return spotify, False

    def _wire_workspace_context(self) -> WorkspaceStore:
        tool_context = self._tools.get_context()
        workspace_store = tool_context.resolve(WorkspaceStore)
        if workspace_store is None:
            workspace_store = WorkspaceStore()
            tool_context.provide(workspace_store)
        return workspace_store

    async def prepare(self) -> None:
        await self._spotify.open()

    async def close(self) -> None:
        if self._owns_spotify:
            await self._spotify.close()

    async def stream(self, task: str) -> AsyncGenerator[AgentEvent, None]:
        self._messages.add_user(task)
        yield RunStartedEvent(message=task)

        for iteration in range(1, self._max_iterations + 1):
            yield StepStartedEvent(step=iteration)
            response = await self._llm.invoke(
                self._messages.all(), tools=self._tool_schema
            )

            if not response.tool_calls:
                output = response.completion or ""
                self._messages.add_assistant(output)
                yield AssistantMessageEvent(content=output)
                yield RunCompletedEvent(output=output)
                return

            self._messages.add_assistant(
                response.completion or "",
                tool_calls=response.tool_calls,
            )

            for call in response.tool_calls:
                args = self._tools.parse_args(call)
                yield ToolCallEvent(name=call.function.name, args=args)
                result = await self._tools.execute(call.function.name, args)
                serialized = self._tools.serialize_result(result)
                yield ToolResultEvent(name=call.function.name, result=serialized)
                for (
                    playlist_draft
                ) in self._workspace_store.drain_playlist_draft_updates():
                    yield WorkspaceUpdatedEvent(playlist_draft=playlist_draft)
                self._messages.add_tool_result(
                    tool_call_id=call.id,
                    content=serialized,
                )

        logger.warning("Max iterations (%d) reached", self._max_iterations)

    def reset(self) -> None:
        self._messages.reset()
