from llmify.messages import ToolCall
import pytest
from pydantic import BaseModel

from agent.tools import ToolContext, Tools
from agent.tools.views import ActionResult, ActionType, Phase
from agent.deck import (
    DeckStore,
    DeckDraftTrack,
)


class _EchoParams(BaseModel):
    value: str


class TestToolsFacadeAbstraction:
    def test_default_tools_include_action_type_metadata(self) -> None:
        tools = Tools()

        assert tools.get("search_tracks") is not None
        assert tools.get("search_tracks").action_type == ActionType.SEARCH
        assert tools.get("search_albums") is None
        assert tools.get("get_artist_albums") is None
        assert tools.get("get_artist_top_tracks") is None
        assert tools.get("get_album_tracks") is None
        assert tools.get("get_spotify_playlist_tracks") is not None
        assert tools.get("get_spotify_playlist_tracks").action_type == ActionType.FETCH
        assert tools.get("create_deck") is None
        assert tools.get("add_deck_tracks") is not None
        assert tools.get("add_deck_tracks").action_type == ActionType.MUTATE
        assert tools.get("ask_onboarding_question") is not None
        assert tools.get("ask_onboarding_question").is_onboarding_question is True

    def test_default_tools_are_filtered_by_phase(self) -> None:
        tools = Tools()

        onboarding_tool_names = {
            schema["function"]["name"]
            for schema in tools.to_schema(phase=Phase.ONBOARDING)
        }
        build_tool_names = {
            schema["function"]["name"] for schema in tools.to_schema(phase=Phase.BUILD)
        }

        assert {
            "ask_onboarding_question",
        }.issubset(onboarding_tool_names)
        assert {
            "search_tracks",
            "search_playlists",
            "get_spotify_playlist_tracks",
            "add_deck_tracks",
            "remove_deck_tracks",
            "replace_deck_tracks",
        }.issubset(build_tool_names)
        assert {
            "search_albums",
            "get_artist_albums",
            "get_artist_top_tracks",
            "get_album_tracks",
        }.isdisjoint(build_tool_names)

    def test_onboarding_question_schema_requires_three_to_six_options(self) -> None:
        tools = Tools()

        schema = next(
            schema
            for schema in tools.to_schema(phase=Phase.ONBOARDING)
            if schema["function"]["name"] == "ask_onboarding_question"
        )
        options = schema["function"]["parameters"]["properties"]["options"]

        assert "options" in schema["function"]["parameters"]["required"]
        assert options["minItems"] == 3
        assert options["maxItems"] == 6

    def test_onboarding_question_schema_exposes_optional_hint(self) -> None:
        tools = Tools()

        schema = next(
            schema
            for schema in tools.to_schema(phase=Phase.ONBOARDING)
            if schema["function"]["name"] == "ask_onboarding_question"
        )
        hint = schema["function"]["parameters"]["properties"]["hint"]

        assert "hint" not in schema["function"]["parameters"]["required"]
        assert "Optional short note" in hint["description"]

    def test_onboarding_question_schema_exposes_selection_mode_enum(self) -> None:
        tools = Tools()

        schema = next(
            schema
            for schema in tools.to_schema(phase=Phase.ONBOARDING)
            if schema["function"]["name"] == "ask_onboarding_question"
        )
        selection_mode = schema["function"]["parameters"]["properties"][
            "selection_mode"
        ]

        assert selection_mode["default"] == "single_select"
        assert selection_mode["enum"] == ["single_select", "multi_select"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "options",
        [
            ["Freunde", "Familie"],
            [str(index) for index in range(7)],
        ],
    )
    async def test_onboarding_question_rejects_option_counts_outside_range(
        self,
        options: list[str],
    ) -> None:
        tools = Tools()

        result = await tools.execute(
            "ask_onboarding_question",
            {
                "question": "Für wen ist die Playlist?",
                "options": options,
            },
            phase=Phase.ONBOARDING,
        )

        assert result.success is False
        assert "options" in (result.error or "")

    def test_custom_tool_phase_metadata_filters_schema_and_lookup(self) -> None:
        tools = Tools()

        @tools.action(
            description="Echo value",
            params=_EchoParams,
            included_in_phases={Phase.BUILD},
        )
        async def echo(params: _EchoParams) -> ActionResult:
            return ActionResult(success=True, extracted_content=params.value)

        onboarding_names = {
            schema["function"]["name"]
            for schema in tools.to_schema(phase=Phase.ONBOARDING)
        }
        build_names = {
            schema["function"]["name"] for schema in tools.to_schema(phase=Phase.BUILD)
        }

        assert "echo" not in onboarding_names
        assert "echo" in build_names
        assert tools.get("echo", phase=Phase.ONBOARDING) is None
        assert tools.get("echo", phase=Phase.BUILD) is not None

    @pytest.mark.asyncio
    async def test_execute_rejects_tool_outside_current_phase(self) -> None:
        tools = Tools()

        result = await tools.execute(
            "search_tracks",
            {"query": "abba", "status": "Suche nach Abba"},
            phase=Phase.ONBOARDING,
        )

        assert result.success is False
        assert "not available in phase 'onboarding'" in (result.error or "")

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

    @pytest.mark.asyncio
    async def test_set_context_updates_executor_dependency_resolution(self) -> None:
        old_store = DeckStore()
        new_store = DeckStore()
        new_store.cache_tracks(
            [
                DeckDraftTrack(
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
            "add_deck_tracks",
            {
                "status": "Tracks ins Deck legen",
                "tracks": [{"uri": "spotify:track:2WfaOiMkCvy7F5fcp2zZ8L"}],
            },
        )

        assert result.success is True
        assert result.extracted_content == (
            '1 track reference(s) processed for Hitster deck "Deck".'
        )
        deck_draft = new_store.draft
        assert deck_draft is not None
        assert deck_draft.name == "Deck"
        assert deck_draft.tracks[0].title == "Take On Me"
        assert old_store.draft is None
        assert new_store.draft is not None
        assert new_store.draft.name == "Deck"
