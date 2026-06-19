from collections.abc import AsyncGenerator, Callable, Sequence
from dataclasses import dataclass, field

from llmify import ChatModel, Message, StreamEnd, StreamEventType
from llmify.messages import ToolCall

from agent.events import (
    AgentEvent,
    AssistantMessageChunkEvent,
    AssistantMessageEvent,
    DeckUpdatedEvent,
    QuestionAskedEvent,
    RunCompletedEvent,
    RunStartedEvent,
    SuspendedForUserInputEvent,
    StepStartedEvent,
    ToolCallEvent,
    ToolResultEvent,
)
from agent.messages import MessageManager
from agent.tools import DeckCritic, Tools, Spotify
from agent.tools.views import Phase
from agent.deck import DeckDraftUpdate, DeckStore
from agent.tokens import TokenTracker
from agent.views import UserEvent


@dataclass
class _LLMResponse:
    completion: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)


class Agent:
    def __init__(
        self,
        llm: ChatModel,
        tools: Tools | None = None,
        history: list[Message] | None = None,
        system_prompt: str | None = None,
        spotify: Spotify | None = None,
        deck_store: DeckStore | None = None,
        max_deck_tracks: int = 50,
        phase: Phase = Phase.ONBOARDING,
    ) -> None:
        self._llm = llm
        self._tools = tools or Tools()
        self._phase = phase

        self._spotify = spotify or Spotify()
        self._tools.provide(self._spotify)

        existing_store = self._tools.resolve(DeckStore)
        self._deck_store = (
            deck_store or existing_store or DeckStore(max_tracks=max_deck_tracks)
        )
        if existing_store is None:
            self._tools.provide(self._deck_store)

        self._messages = MessageManager(
            system_prompt=system_prompt,
            phase=phase,
            deck_draft_provider=lambda: self._deck_store.draft,
            max_deck_tracks=max_deck_tracks,
            history=history,
        )

        self._critic = DeckCritic(
            llm,
            deck_store=self._deck_store,
            message_manager=self._messages,
            target_size=max_deck_tracks,
        )
        self._tools.provide(self._critic)

        self._token_tracker = TokenTracker()
        self._llm_name = type(llm).__name__

        self._stop_requested = False

    @property
    def phase(self) -> Phase:
        return self._phase

    async def close(self) -> None:
        await self._spotify.close()

    def request_stop(self) -> None:
        self._stop_requested = True

    async def stream(
        self,
        message: str | None = None,
        curation_events: Sequence[UserEvent] | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        self._stop_requested = False
        if message is not None or curation_events:
            self._messages.add_user(message or "", curation_events)
            yield RunStartedEvent(message=message or "")

        async for event in self._run_loop():
            yield event

    async def _run_loop(self) -> AsyncGenerator[AgentEvent, None]:
        iteration = 0
        while True:
            iteration += 1
            if self._stop_requested:
                return
            yield StepStartedEvent(step=iteration)

            response = _LLMResponse()
            async for event in self._stream_llm_response(response):
                yield event
            if self._stop_requested:
                return

            if not response.tool_calls:
                for event in self._run_completion_guardrails():
                    yield event
                self._messages.add_assistant(response.completion)
                yield AssistantMessageEvent(content=response.completion)
                yield RunCompletedEvent(output=response.completion)
                return

            if response.completion:
                yield AssistantMessageEvent(content=response.completion)

            self._messages.add_assistant(
                response.completion,
                tool_calls=response.tool_calls,
            )

            for call in response.tool_calls:
                if self._stop_requested:
                    return
                async for event in self._handle_tool_call(call):
                    yield event
                    if isinstance(event, SuspendedForUserInputEvent):
                        return

    async def _stream_llm_response(
        self,
        response: _LLMResponse,
    ) -> AsyncGenerator[AgentEvent, None]:
        schemas = self._tools.to_schema(phase=self._phase)
        async for event in self._llm.stream(self._messages.all(), tools=schemas):
            if self._stop_requested:
                return
            if event.type == StreamEventType.TEXT:
                if event.delta:
                    response.completion += event.delta
                    yield AssistantMessageChunkEvent(chunk=event.delta)
            elif event.type == StreamEventType.TOOL_CALL:
                response.tool_calls.append(event.tool_call)
            elif event.type == StreamEventType.END:
                assert isinstance(event, StreamEnd)
                response.completion = event.completion or response.completion
                if event.tool_calls:
                    response.tool_calls = event.tool_calls
                self._token_tracker.add(event.usage, self._llm_name)

    async def _handle_tool_call(
        self,
        call: ToolCall,
    ) -> AsyncGenerator[AgentEvent, None]:
        args = self._tools.parse_args(call)
        tool = self._tools.get(call.function.name, phase=self._phase)
        is_onboarding_question = tool.is_onboarding_question if tool else False
        if not is_onboarding_question:
            yield ToolCallEvent(
                tool_call_id=call.id,
                name=call.function.name,
                args=args,
                status_label=tool.render_status(args) if tool else None,
                action_type=tool.action_type if tool else None,
                is_onboarding_question=False,
            )

        result = await self._tools.execute(
            call.function.name,
            args,
            phase=self._phase,
        )
        content = result.to_content()
        if not is_onboarding_question:
            yield ToolResultEvent(
                tool_call_id=call.id,
                name=call.function.name,
                result=content,
            )
        for update in self._deck_store.drain_deck_draft_updates():
            yield self._to_deck_updated_event(update)
        self._messages.add_tool_result(
            tool_call_id=call.id,
            content=content,
        )
        request = result.input_request
        if request is not None:
            if request.is_last_question:
                yield SuspendedForUserInputEvent(
                    question=request.question,
                    hint=request.hint,
                    options=list(request.options),
                    recommended_option=request.recommended_option,
                    selection_mode=request.selection_mode,
                )
            else:
                yield QuestionAskedEvent(
                    question=request.question,
                    hint=request.hint,
                    options=list(request.options),
                    recommended_option=request.recommended_option,
                    selection_mode=request.selection_mode,
                )

    def _run_completion_guardrails(self) -> list[DeckUpdatedEvent]:
        # The LLM has ended its tool loop here; keep final deck state deterministic
        # before publishing the assistant completion.
        if self._deck_store.remove_duplicate_tracks() is None:
            return []
        return self._drain_deck_draft_update_events()

    def _drain_deck_draft_update_events(self) -> list[DeckUpdatedEvent]:
        return [
            self._to_deck_updated_event(update)
            for update in self._deck_store.drain_deck_draft_updates()
        ]

    def _to_deck_updated_event(self, update: DeckDraftUpdate) -> DeckUpdatedEvent:
        return DeckUpdatedEvent(
            deck_draft=update.deck_draft,
            update=update,
        )
