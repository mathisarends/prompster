import asyncio
import json
from collections.abc import AsyncIterator, Callable, Mapping, Sequence
from typing import Any

import pytest
from agent.research import FoundTrack, Spotify, TrackResults
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import (
    AgentInfo,
    DeltaToolCall,
    DeltaToolCalls,
    FunctionModel,
)

type ToolCalls = Mapping[str, tuple[str, Mapping[str, Any]]]
type ScriptStep = str | tuple[str, ...] | ToolCalls | Exception


class ScriptedLlm:
    """A pydantic_ai model that plays back scripted steps without any network.

    A string is one text reply, a tuple is a text reply in chunks, a mapping of
    ``call_id -> (tool, args)`` is a tool-call step, and an exception is raised.
    """

    def __init__(
        self, steps: Sequence[ScriptStep], *, model_name: str = "scripted"
    ) -> None:
        self._steps = list(steps)
        self.requests: list[list[ModelMessage]] = []
        self.infos: list[AgentInfo] = []
        self.model = FunctionModel(
            self._respond,
            stream_function=self._stream,
            model_name=model_name,
        )

    @property
    def tool_names(self) -> list[set[str]]:
        return [{tool.name for tool in info.function_tools} for info in self.infos]

    def _next(self, messages: list[ModelMessage], info: AgentInfo) -> ScriptStep:
        self.requests.append(list(messages))
        self.infos.append(info)
        step = self._steps.pop(0)
        if isinstance(step, Exception):
            raise step
        return step

    def _respond(self, messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        step = self._next(messages, info)
        if isinstance(step, Mapping):
            return ModelResponse(
                parts=[
                    ToolCallPart(name, json.dumps(args), tool_call_id=call_id)
                    for call_id, (name, args) in step.items()
                ]
            )
        text = step if isinstance(step, str) else "".join(step)
        return ModelResponse(parts=[TextPart(text)])

    async def _stream(
        self,
        messages: list[ModelMessage],
        info: AgentInfo,
    ) -> AsyncIterator[str | DeltaToolCalls]:
        step = self._next(messages, info)
        if isinstance(step, Mapping):
            yield {
                index: DeltaToolCall(name, json.dumps(args), tool_call_id=call_id)
                for index, (call_id, (name, args)) in enumerate(step.items())
            }
            return
        for chunk in (step,) if isinstance(step, str) else step:
            yield chunk


@pytest.fixture
def scripted_llm() -> Callable[..., ScriptedLlm]:
    def create(*steps: ScriptStep, model_name: str = "scripted") -> ScriptedLlm:
        return ScriptedLlm(steps, model_name=model_name)

    return create


class FakeSpotify(Spotify):
    """Answers track searches from a fixed catalog, without any network."""

    def __init__(self, *tracks: FoundTrack, gate: asyncio.Event | None = None) -> None:
        super().__init__()
        self._tracks = tracks
        self._gate = gate
        self.searches: list[str] = []

    async def open(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def search_tracks(self, query: str, *, limit: int = 10) -> TrackResults:
        del limit
        self.searches.append(query)
        if self._gate is not None:
            await self._gate.wait()
        content = "\n".join(f'<track uri="{track.uri}" />' for track in self._tracks)
        return TrackResults(content=content or "No tracks found.", tracks=self._tracks)


TAKE_ON_ME = FoundTrack(
    uri="spotify:track:2WfaOiMkCvy7F5fcp2zZ8L",
    title="Take On Me",
    artist="a-ha",
    year=1985,
)
