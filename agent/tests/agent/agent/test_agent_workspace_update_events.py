import json
from dataclasses import dataclass
from typing import Any

from llmify.messages import ToolCall
import pytest

from agent.agent import Agent, ToolResultEvent, WorkspaceUpdatedEvent
from agent.tools import ToolContext, Tools
from agent.workspace import WorkspaceStore


@dataclass
class _ChatResponse:
    completion: str | None
    tool_calls: list[ToolCall]


class _FakeLlm:
    def __init__(self, responses: list[_ChatResponse]) -> None:
        self._responses = responses

    async def invoke(self, messages: list[Any], tools: list[Any]) -> _ChatResponse:
        return self._responses.pop(0)


class TestAgentWorkspaceUpdateEvents:
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
