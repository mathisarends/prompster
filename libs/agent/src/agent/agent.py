import asyncio
from collections.abc import AsyncGenerator, Sequence
from dataclasses import dataclass, field

from callm import (
    ChatModel,
    ContextLengthExceededError,
    Message,
    ModelResponse,
    TextDelta,
    ToolCall,
)
from spotifyify import RetryEvent

from agent.deck import DeckDraftUpdate, DeckStore
from agent.events import (
    AgentEvent,
    AssistantMessageChunkEvent,
    AssistantMessageEvent,
    ContextCompactedEvent,
    DeckUpdatedEvent,
    QuestionAskedEvent,
    RunCompletedEvent,
    RunStartedEvent,
    StepStartedEvent,
    SuspendedForUserInputEvent,
    ToolCallEvent,
    ToolCallSequenceStartedEvent,
    ToolResultEvent,
    ToolRetryEvent,
)
from agent.guardrails import PostRunGuardrails
from agent.messages import MessageManager
from agent.tokens import TokenTracker
from agent.tools import DeckCritic, Spotify, Tools
from agent.tools.params import SequenceLabelParams, ToolParams
from agent.tools.retry_reporting import retry_sink
from agent.views import Phase, UserEvent


@dataclass
class _LLMResponse:
    completion: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    provider_state: object | None = None


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
        max_input_tokens: int | None = None,
        compaction_threshold: float = 0.8,
    ) -> None:
        self._llm = llm
        self._tools = tools or Tools()
        self._phase = phase

        input_token_limit = max_input_tokens or 272_000
        self._compaction_budget = int(input_token_limit * compaction_threshold)
        self._last_prompt_tokens = 0

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

        self._guardrails = PostRunGuardrails(self._deck_store)

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

            for event in self._compact_proactively():
                yield event

            response = _LLMResponse()
            async for event in self._stream_llm_response_with_recovery(response):
                yield event
            if self._stop_requested:
                return

            if not response.tool_calls:
                for event in await self._run_completion_guardrails():
                    yield event
                self._messages.add_assistant(
                    response.completion,
                    provider_state=response.provider_state,
                )
                yield AssistantMessageEvent(content=response.completion)
                yield RunCompletedEvent(output=response.completion)
                return

            if response.completion:
                yield AssistantMessageEvent(content=response.completion)

            self._messages.add_assistant(
                response.completion,
                tool_calls=response.tool_calls,
                provider_state=response.provider_state,
            )
            yield ToolCallSequenceStartedEvent(
                label=self._tool_call_sequence_label(response.tool_calls)
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
        tools = self._tools.to_model_tools(phase=self._phase)
        async for event in self._llm.stream(self._messages.all(), tools=tools):
            if self._stop_requested:
                return
            match event:
                case TextDelta(delta=delta) if delta:
                    response.completion += delta
                    yield AssistantMessageChunkEvent(chunk=delta)
                case ModelResponse():
                    response.completion = event.completion or response.completion
                    response.tool_calls = list(event.tool_calls)
                    response.provider_state = event.provider_state
                    self._token_tracker.add(event.usage, self._llm_name)
                    self._last_prompt_tokens = event.usage.input_tokens

    def _compact_proactively(self) -> list[ContextCompactedEvent]:
        # The last observed prompt size already exceeds our safety budget, so
        # compact before issuing the next call instead of risking the provider's
        # hard context-length error.
        if self._last_prompt_tokens < self._compaction_budget:
            return []
        compacted = self._messages.compact_tool_results()
        if compacted == 0:
            return []
        event = ContextCompactedEvent(
            reason="proactive",
            tokens_before=self._last_prompt_tokens,
            compacted_tool_results=compacted,
        )
        # Reset so the estimate reflects the freshly compacted history and we do
        # not keep compacting on every subsequent iteration.
        self._last_prompt_tokens = 0
        return [event]

    async def _stream_llm_response_with_recovery(
        self,
        response: _LLMResponse,
    ) -> AsyncGenerator[AgentEvent, None]:
        try:
            async for event in self._stream_llm_response(response):
                yield event
            return
        except ContextLengthExceededError:
            compacted = self._messages.compact_tool_results(keep_last=2)
            yield ContextCompactedEvent(
                reason="reactive",
                tokens_before=self._last_prompt_tokens,
                compacted_tool_results=compacted,
            )
            if compacted == 0:
                raise

        response.completion = ""
        response.tool_calls = []
        response.provider_state = None
        async for event in self._stream_llm_response(response):
            yield event

    def _tool_call_sequence_label(self, calls: list[ToolCall]) -> str | None:
        params = [self._tools.parse_params(call, phase=self._phase) for call in calls]

        for param in params:
            if not isinstance(param, SequenceLabelParams):
                continue
            label = self._clean_sequence_label(param.sequence_label)
            if label is not None:
                return label

        for param in params:
            if not isinstance(param, ToolParams):
                continue
            label = self._clean_sequence_label(param.status)
            if label is not None:
                return label

        return None

    @staticmethod
    def _clean_sequence_label(value: str | None) -> str | None:
        if value is None:
            return None
        label = " ".join(value.split())
        if not label:
            return None
        if len(label) > 80:
            return f"{label[:77].rstrip()}..."
        return label

    async def _handle_tool_call(
        self,
        call: ToolCall,
    ) -> AsyncGenerator[AgentEvent, None]:
        args = self._tools.parse_args(call)
        tool = self._tools.get(call.name, phase=self._phase)
        is_onboarding_question = tool.is_onboarding_question if tool else False
        if not is_onboarding_question:
            yield ToolCallEvent(
                tool_call_id=call.id,
                name=call.name,
                args=args,
                status_label=tool.render_status(args) if tool else None,
                action_type=tool.action_type if tool else None,
                is_onboarding_question=False,
            )

        retries: asyncio.Queue[RetryEvent] = asyncio.Queue()
        with retry_sink(retries.put_nowait):
            exec_task = asyncio.create_task(
                self._tools.execute(call.name, args, phase=self._phase)
            )
            while True:
                getter = asyncio.create_task(retries.get())
                done, _ = await asyncio.wait(
                    {exec_task, getter},
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if getter in done:
                    retry = getter.result()
                    if not is_onboarding_question:
                        yield self._to_tool_retry_event(call, retry)
                else:
                    getter.cancel()
                if exec_task in done:
                    break
            result = exec_task.result()
            while not retries.empty():
                if not is_onboarding_question:
                    yield self._to_tool_retry_event(call, retries.get_nowait())
        content = result.to_content()
        if not is_onboarding_question:
            yield ToolResultEvent(
                tool_call_id=call.id,
                name=call.name,
                result=content,
                items=list(result.items),
            )
        for update in self._deck_store.drain_deck_draft_updates():
            yield self._to_deck_updated_event(update)
        self._messages.add_tool_result(
            tool_call_id=call.id,
            tool_name=call.name,
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

    async def _run_completion_guardrails(self) -> list[DeckUpdatedEvent]:
        # The LLM has ended its tool loop here; keep final deck state deterministic
        # before publishing the assistant completion.
        return [
            self._to_deck_updated_event(update)
            for update in await self._guardrails.run()
        ]

    def _to_tool_retry_event(self, call: ToolCall, retry: RetryEvent) -> ToolRetryEvent:
        return ToolRetryEvent(
            tool_call_id=call.id,
            name=call.name,
            attempt=retry.retry_number,
            max_attempts=retry.max_retries,
            retry_in_seconds=retry.retry_in_seconds,
            status_code=retry.status_code,
        )

    def _to_deck_updated_event(self, update: DeckDraftUpdate) -> DeckUpdatedEvent:
        return DeckUpdatedEvent(
            deck_draft=update.deck_draft,
            update=update,
        )
