import json
from datetime import datetime, timezone

from llmify.messages import ToolCall
import pytest
from pydantic import BaseModel

from agent.tools import ToolContext, Tools
from agent.tools.views import ActionType
from agent.workspace import WorkspaceStore


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
        assert tools.get("build_draft_playlist") is not None
        assert tools.get("build_draft_playlist").action_type == ActionType.MUTATE
        assert tools.get("ask_follow_up") is not None
        assert tools.get("ask_follow_up").action_type == ActionType.INTERACT

    @pytest.mark.asyncio
    async def test_action_registers_and_executes_custom_tool(self) -> None:
        tools = Tools()

        @tools.action(description="Echo value", params=_EchoParams)
        async def echo(params: _EchoParams) -> str:
            return params.value

        result = await tools.execute("echo", {"value": "ok"})

        assert result == "ok"

    def test_parse_args_returns_dict_for_valid_json(self) -> None:
        tool_call = ToolCall(
            id="call-1",
            function={"name": "search_tracks", "arguments": '{"query": "abba"}'},
        )

        parsed = Tools.parse_args(tool_call)

        assert parsed == {"query": "abba"}

    def test_parse_args_returns_empty_dict_for_invalid_json(self) -> None:
        tool_call = ToolCall(
            id="call-1",
            function={"name": "search_tracks", "arguments": "{not-json"},
        )

        parsed = Tools.parse_args(tool_call)

        assert parsed == {}

    def test_serialize_result_handles_string_model_and_dict(self) -> None:
        model_result = _ResultModel(value=3)
        dict_result = {"now": datetime(2026, 5, 19, tzinfo=timezone.utc)}

        serialized_string = Tools.serialize_result("plain")
        serialized_model = Tools.serialize_result(model_result)
        serialized_dict = Tools.serialize_result(dict_result)

        assert serialized_string == "plain"
        assert json.loads(serialized_model) == {"value": 3}
        assert "2026-05-19" in serialized_dict

    @pytest.mark.asyncio
    async def test_set_context_updates_executor_dependency_resolution(self) -> None:
        old_store = WorkspaceStore()
        new_store = WorkspaceStore()
        tools = Tools(ToolContext(old_store))
        tools.set_context(ToolContext(new_store))

        result = await tools.execute(
            "build_draft_playlist",
            {
                "name": "Context Switch",
                "status": "Playlist-Entwurf bauen",
                "tracks": [
                    {
                        "title": "Take On Me",
                        "artist": "a-ha",
                        "year": 1985,
                        "spotify_uri": "spotify:track:2WfaOiMkCvy7F5fcp2zZ8L",
                        "cover_url": "https://i.scdn.co/image/take-on-me.jpg",
                    }
                ],
            },
        )

        assert result.name == "Context Switch"
        assert old_store.playlist_draft is None
        assert new_store.playlist_draft is not None
        assert new_store.playlist_draft.name == "Context Switch"
