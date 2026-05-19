import logging
from collections.abc import AsyncGenerator

from llmify import ChatModel

from agent.agent.events import (
    AgentEvent,
    AssistantMessageEvent,
    FollowUpRequestedEvent,
    RunCompletedEvent,
    RunStartedEvent,
    StepStartedEvent,
    ToolCallEvent,
    ToolResultEvent,
    WorkspaceUpdatedEvent,
)
from agent.agent.messages.messages import MessageManager
from agent.tools import Tools, Spotify
from agent.tools.views import AskFollowUpParams
from agent.workspace import WorkspaceStore

logger = logging.getLogger(__name__)


class Agent:
    def __init__(
        self,
        llm: ChatModel,
        tools: Tools | None = None,
        messages: MessageManager | None = None,
        max_iterations: int = 10,
        system_prompt: str | None = None,
        spotify: Spotify | None = None,
        workspace_store: WorkspaceStore | None = None,
    ) -> None:
        self._llm = llm
        self._tools = tools or Tools()
        self._max_iterations = max_iterations
        self._messages = messages or MessageManager(system_prompt=system_prompt)

        if spotify is not None:
            self._spotify = spotify
            self._owns_spotify = False
        else:
            self._spotify = Spotify()
            self._owns_spotify = True
        self._tools.get_context().provide(self._spotify)

        existing_workspace_store = self._tools.get_context().resolve(WorkspaceStore)
        self._workspace_store = (
            workspace_store or existing_workspace_store or WorkspaceStore()
        )
        if existing_workspace_store is None:
            self._tools.get_context().provide(self._workspace_store)

        self._tool_schema = self._tools.to_schema()

    async def prepare(self) -> None:
        await self._spotify.open()

    async def close(self) -> None:
        if self._owns_spotify:
            await self._spotify.close()

    async def stream(self, message: str) -> AsyncGenerator[AgentEvent, None]:
        self._messages.add_user(message)
        yield RunStartedEvent(message=message)
        async for event in self._run_loop():
            yield event

    async def resume(
        self, tool_call_id: str, answer: str
    ) -> AsyncGenerator[AgentEvent, None]:
        self._messages.add_tool_result(tool_call_id=tool_call_id, content=answer)
        async for event in self._run_loop():
            yield event

    def reset(self) -> None:
        self._messages.reset()

    async def _run_loop(self) -> AsyncGenerator[AgentEvent, None]:
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

                tool = self._tools.get(call.function.name)
                if tool is not None and tool.suspends_for_input:
                    parsed = AskFollowUpParams.model_validate(args)
                    yield FollowUpRequestedEvent(
                        tool_call_id=call.id,
                        questions=parsed.questions,
                    )
                    return  # suspend — resume() injects the answer as tool result

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
