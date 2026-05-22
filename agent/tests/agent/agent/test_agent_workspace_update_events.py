import json
from dataclasses import dataclass
from typing import Any

from llmify import StreamEnd, StreamTextDelta, StreamToolCall
from llmify.messages import ToolCall
import pytest

from agent.agent import (
    Agent,
    AssistantMessageChunkEvent,
    AssistantMessageEvent,
    ToolResultEvent,
    WorkspaceUpdatedEvent,
)
from agent.tools import ToolContext, Tools
from agent.workspace import WorkspaceStore


@dataclass
class _ChatResponse:
    completion: str | None
    tool_calls: list[ToolCall]
    chunks: list[str] | None = None


class _FakeLlm:
    def __init__(self, responses: list[_ChatResponse]) -> None:
        self._responses = responses

    async def stream(self, messages: list[Any], tools: list[Any]):
        response = self._responses.pop(0)
        for chunk in response.chunks or []:
            yield StreamTextDelta(delta=chunk)
        for tool_call in response.tool_calls:
            yield StreamToolCall(tool_call=tool_call)
        yield StreamEnd(
            completion=response.completion or "",
            tool_calls=response.tool_calls,
        )


class TestAgentWorkspaceUpdateEvents:
    @pytest.mark.asyncio
    async def test_stream_emits_assistant_chunks_before_completed_message(self) -> None:
        llm = _FakeLlm(
            [
                _ChatResponse(
                    completion="Hallo Welt",
                    chunks=["Hallo", " Welt"],
                    tool_calls=[],
                )
            ]
        )
        agent = Agent(llm=llm)

        events = [event async for event in agent.stream("Sag hallo")]

        chunks = [
            event.chunk
            for event in events
            if isinstance(event, AssistantMessageChunkEvent)
        ]
        completed = next(
            event for event in events if isinstance(event, AssistantMessageEvent)
        )

        assert chunks == ["Hallo", " Welt"]
        assert completed.content == "Hallo Welt"

    @pytest.mark.asyncio
    async def test_stream_emits_workspace_update_after_tool_result(self) -> None:
        workspace_store = WorkspaceStore()
        tools = Tools(ToolContext(workspace_store))
        tool_args = {
            "name": "80er Party",
            "tracks": [
                {
                    "title": "Take On Me",
                    "artist": "a-ha",
                    "year": 1985,
                    "spotify_uri": "spotify:track:2WfaOiMkCvy7F5fcp2zZ8L",
                    "cover_url": "https://i.scdn.co/image/take-on-me.jpg",
                }
            ],
        }
        llm = _FakeLlm(
            [
                _ChatResponse(
                    completion="",
                    tool_calls=[
                        ToolCall(
                            id="call-1",
                            function={
                                "name": "build_draft_playlist",
                                "arguments": json.dumps(tool_args),
                            },
                        )
                    ],
                ),
                _ChatResponse(completion="Der Entwurf ist bereit.", tool_calls=[]),
            ]
        )
        agent = Agent(llm=llm, tools=tools)

        events = [event async for event in agent.stream("Bau mir ein Deck")]

        tool_result_index = next(
            index
            for index, event in enumerate(events)
            if isinstance(event, ToolResultEvent)
        )
        workspace_update_index = next(
            index
            for index, event in enumerate(events)
            if isinstance(event, WorkspaceUpdatedEvent)
        )
        tool_result = events[tool_result_index]
        workspace_update = events[workspace_update_index]

        assert workspace_update_index == tool_result_index + 1
        assert isinstance(tool_result, ToolResultEvent)
        assert isinstance(workspace_update, WorkspaceUpdatedEvent)
        assert json.loads(tool_result.result)["name"] == "80er Party"
        assert workspace_update.playlist_draft.name == "80er Party"
        assert workspace_update.playlist_draft.tracks[0].title == "Take On Me"
        assert workspace_store.drain_playlist_draft_updates() == []
