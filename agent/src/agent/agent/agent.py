import logging
from collections.abc import AsyncGenerator

from llmify import ChatModel, Message, StreamEventType

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
from agent.playlist import PlaylistDraftStore
from agent.agent.views import UserEvents

logger = logging.getLogger(__name__)


class Agent:
    def __init__(
        self,
        llm: ChatModel,
        tools: Tools | None = None,
        history: list[Message] | None = None,
        user_events: UserEvents | None = None,
        max_iterations: int = 10,
        system_prompt: str | None = None,
        spotify: Spotify | None = None,
        playlist_store: PlaylistDraftStore | None = None,
    ) -> None:
        self._llm = llm
        self._tools = tools or Tools()
        self._max_iterations = max_iterations

        self._spotify = spotify or Spotify()
        self._tools.provide(self._spotify)

        existing_store = self._tools.resolve(PlaylistDraftStore)
        self._playlist_store = playlist_store or existing_store or PlaylistDraftStore()
        if existing_store is None:
            self._tools.provide(self._playlist_store)
        self._user_events = list(user_events or [])

        self._messages = MessageManager(
            system_prompt=system_prompt,
            playlist_draft_provider=lambda: self._playlist_store.playlist_draft,
            user_events_provider=lambda: self._user_events,
            history=history,
        )

        self._tool_schema = self._tools.to_schema()

    async def close(self) -> None:
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
                tool = self._tools.get(call.function.name)
                yield ToolCallEvent(
                    tool_call_id=call.id,
                    name=call.function.name,
                    args=args,
                    status_label=tool.render_status(args) if tool else None,
                    action_type=tool.action_type if tool else None,
                )

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
                for update in self._playlist_store.drain_playlist_draft_updates():
                    yield WorkspaceUpdatedEvent(
                        playlist_draft=update.playlist_draft,
                        update=update,
                    )
                self._messages.add_tool_result(
                    tool_call_id=call.id,
                    content=serialized,
                )

        logger.warning("Max iterations (%d) reached", self._max_iterations)
