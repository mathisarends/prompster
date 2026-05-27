import json

from llmify.messages import ToolCall
import pytest
from pydantic import BaseModel

from agent.tools import ToolContext, Tools
from agent.tools.views import ActionResult, ActionType
from agent.playlist import (
    PlaylistDraftStore,
    PlaylistDraftToolResult,
    PlaylistDraftTrack,
)


class _EchoParams(BaseModel):
    value: str


class _ResultModel(BaseModel):
    value: int


class TestToolsFacadeAbstraction:
    def test_default_tools_include_action_type_metadata(self) -> None:
        tools = Tools()

        assert tools.get("search_tracks") is not None
        assert tools.get("search_tracks").action_type == ActionType.SEARCH
        assert tools.get("get_album_tracks") is not None
        assert tools.get("get_album_tracks").action_type == ActionType.FETCH
        assert tools.get("create_playlist") is not None
        assert tools.get("create_playlist").action_type == ActionType.MUTATE
        assert tools.get("add_playlist_tracks") is not None
        assert tools.get("add_playlist_tracks").action_type == ActionType.MUTATE
        assert tools.get("ask_follow_up") is not None
        assert tools.get("ask_follow_up").action_type == ActionType.INTERACT

    @pytest.mark.asyncio
    async def test_action_registers_and_executes_custom_tool(self) -> None:
        tools = Tools()

        @tools.action(description="Echo value", params=_EchoParams)
        async def echo(params: _EchoParams) -> ActionResult:
            return ActionResult(success=True, extracted_content=params.value)

        result = await tools.execute("echo", {"value": "ok"})

        assert result == ActionResult(success=True, extracted_content="ok")

    def test_parse_args_returns_dict_for_valid_json(self) -> None:
        tools = Tools()
        tool_call = ToolCall(
            id="call-1",
            function={"name": "search_tracks", "arguments": '{"query": "abba"}'},
        )

        parsed = tools.parse_args(tool_call)

        assert parsed == {"query": "abba"}

    def test_parse_args_returns_empty_dict_for_invalid_json(self) -> None:
        tools = Tools()
        tool_call = ToolCall(
            id="call-1",
            function={"name": "search_tracks", "arguments": "{not-json"},
        )

        parsed = tools.parse_args(tool_call)

        assert parsed == {}

    def test_serialize_result_serializes_action_result_contract(self) -> None:
        tools = Tools()
        serialized = tools.serialize_result(
            ActionResult(
                success=True,
                extracted_content=_ResultModel(value=3),
            )
        )

        assert json.loads(serialized) == {
            "success": True,
            "extracted_content": {"value": 3},
            "error": None,
        }

    @pytest.mark.asyncio
    async def test_set_context_updates_executor_dependency_resolution(self) -> None:
        old_store = PlaylistDraftStore()
        new_store = PlaylistDraftStore()
        new_store.cache_tracks(
            [
                PlaylistDraftTrack(
                    title="Take On Me",
                    artist="a-ha",
                    year=1985,
                    spotify_uri="spotify:track:2WfaOiMkCvy7F5fcp2zZ8L",
                    cover_url="https://i.scdn.co/image/take-on-me.jpg",
                )
            ]
        )
        tools = Tools(ToolContext(old_store))
        tools.set_context(ToolContext(new_store))

        result = await tools.execute(
            "create_playlist",
            {
                "name": "Context Switch",
                "status": "Tracks ins Deck legen",
            },
        )

        assert result.success is True
        tool_result = result.extracted_content
        assert isinstance(tool_result, PlaylistDraftToolResult)
        playlist_draft = tool_result.playlist_draft
        assert playlist_draft is not None
        assert playlist_draft.name == "Context Switch"
        assert old_store.playlist_draft is None
        assert new_store.playlist_draft is not None
        assert new_store.playlist_draft.name == "Context Switch"
        assert new_store.playlist_draft.tracks == []
