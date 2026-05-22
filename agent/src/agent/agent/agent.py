import logging
from collections.abc import AsyncGenerator

from llmify import ChatModel, StreamEventType

from agent.agent.events import (
    AgentEvent,
    AssistantMessageChunkEvent,
    AssistantMessageEvent,
    FollowUpRequestedEvent,
    RunCompletedEvent,
    RunStartedEvent,
    StepStartedEvent,
    ToolCallEvent,
    ToolResultEvent,
    WorkspaceUpdatedEvent,
)
from agent.agent.messages import MessageManager
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
        async for event in self.continue_stream():
            yield event

    async def resume(
        self, tool_call_id: str, answer: str
    ) -> AsyncGenerator[AgentEvent, None]:
        self._messages.add_tool_result(tool_call_id=tool_call_id, content=answer)
        async for event in self.continue_stream():
            yield event

    async def continue_stream(self) -> AsyncGenerator[AgentEvent, None]:
        async for event in self._run_loop():
            yield event

    def reset(self) -> None:
        self._messages.reset()

    async def _run_loop(self) -> AsyncGenerator[AgentEvent, None]:
        for iteration in range(1, self._max_iterations + 1):
            yield StepStartedEvent(step=iteration)
            completion = ""
            tool_calls = []

            async for response_event in self._llm.stream(
                self._messages.all(), tools=self._tool_schema
            ):
                if response_event.type == StreamEventType.TEXT:
                    if response_event.delta:
                        completion += response_event.delta
                        yield AssistantMessageChunkEvent(chunk=response_event.delta)
                elif response_event.type == StreamEventType.TOOL_CALL:
                    tool_calls.append(response_event.tool_call)
                elif response_event.type == StreamEventType.END:
                    completion = response_event.completion or completion
                    if response_event.tool_calls:
                        tool_calls = response_event.tool_calls

            if not tool_calls:
                self._messages.add_assistant(completion)
                yield AssistantMessageEvent(content=completion)
                yield RunCompletedEvent(output=completion)
                return

            if completion:
                yield AssistantMessageEvent(content=completion)

            self._messages.add_assistant(
                completion,
                tool_calls=tool_calls,
            )

            for call in tool_calls:
                args = self._tools.parse_args(call)
                yield ToolCallEvent(
                    tool_call_id=call.id,
                    name=call.function.name,
                    args=args,
                    status_label=self._tools.render_status(call.function.name, args),
                )

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
                yield ToolResultEvent(
                    tool_call_id=call.id,
                    name=call.function.name,
                    result=serialized,
                )
                for (
                    playlist_draft
                ) in self._workspace_store.drain_playlist_draft_updates():
                    yield WorkspaceUpdatedEvent(playlist_draft=playlist_draft)
                self._messages.add_tool_result(
                    tool_call_id=call.id,
                    content=serialized,
                )

        logger.warning("Max iterations (%d) reached", self._max_iterations)
