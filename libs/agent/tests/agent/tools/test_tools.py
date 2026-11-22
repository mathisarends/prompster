import pytest
from agent.deck import (
    DeckDraft,
    DeckDraftTrack,
    DeckStore,
    TrackRef,
)
from agent.tools import ToolContext, Tools
from agent.tools.handler import Spotify
from agent.tools.handler.spotify_rendering import SpotifyTrackLookupResult
from agent.tools.params import SearchParams
from agent.tools.views import ActionResult, ActionType
from agent.views import Phase
from callm import ToolCall
from pydantic import BaseModel


class _EchoParams(BaseModel):
    value: str


class TestToolsFacadeAbstraction:
    def test_default_tools_include_action_type_metadata(self) -> None:
        tools = Tools()

        assert tools.get("search_tracks") is not None
        assert tools.get("search_tracks").action_type == ActionType.SEARCH_TRACKS
        assert tools.get("search_playlists").action_type == ActionType.SEARCH_PLAYLISTS
        assert tools.get("search_albums") is None
        assert tools.get("get_artist_albums") is None
        assert tools.get("get_artist_top_tracks") is None
        assert tools.get("get_album_tracks") is None
        assert tools.get("get_spotify_playlist_tracks") is not None
        assert (
            tools.get("get_spotify_playlist_tracks").action_type
            == ActionType.GET_SPOTIFY_PLAYLIST_TRACKS
        )
        assert tools.get("review_deck").action_type == ActionType.SELF_REVIEW
        assert tools.get("create_deck") is None
        assert tools.get("add_deck_tracks") is not None
        assert tools.get("add_deck_tracks").action_type == ActionType.ADD_DECK_TRACKS
        assert (
            tools.get("remove_deck_tracks").action_type == ActionType.REMOVE_DECK_TRACKS
        )
        assert (
            tools.get("replace_deck_tracks").action_type
            == ActionType.REPLACE_DECK_TRACKS
        )
        assert tools.get("ask_onboarding_question") is not None
        assert (
            tools.get("ask_onboarding_question").action_type
            == ActionType.ASK_ONBOARDING_QUESTION
        )
        assert tools.get("ask_onboarding_question").is_onboarding_question is True

    def test_default_tools_are_filtered_by_phase(self) -> None:
        tools = Tools()

        onboarding_tool_names = {
            tool.name for tool in tools.to_model_tools(phase=Phase.ONBOARDING)
        }
        build_tool_names = {
            tool.name for tool in tools.to_model_tools(phase=Phase.BUILD)
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

    def test_onboarding_question_schema_requires_two_to_four_options(self) -> None:
        tools = Tools()

        tool = next(
            tool
            for tool in tools.to_model_tools(phase=Phase.ONBOARDING)
            if tool.name == "ask_onboarding_question"
        )
        options = tool.parameters["properties"]["options"]

        assert "options" in tool.parameters["required"]
        assert options["minItems"] == 2
        assert options["maxItems"] == 4

    def test_spotify_research_tools_do_not_expose_generated_status(self) -> None:
        tools = Tools()

        schemas = {
            tool.name: tool.parameters
            for tool in tools.to_model_tools(phase=Phase.BUILD)
        }

        assert "status" not in schemas["search_tracks"]["properties"]
        assert "status" not in schemas["search_playlists"]["properties"]
        assert "status" not in schemas["get_spotify_playlist_tracks"]["properties"]
        assert "playlist_name" in schemas["get_spotify_playlist_tracks"]["required"]

    def test_spotify_research_tool_statuses_are_derived_from_params(self) -> None:
        tools = Tools()

        assert tools.get("search_tracks").render_status({"query": "ABBA"}) == (
            "Suche Tracks: ABBA"
        )
        assert tools.get("search_playlists").render_status(
            {"query": "Italo Disco"}
        ) == ("Suche Playlists: Italo Disco")
        assert (
            tools.get("get_spotify_playlist_tracks").render_status(
                {"playlist_id": "spotify:playlist:123", "playlist_name": "This Is ABBA"}
            )
            == "Hole Playlist-Tracks: This Is ABBA"
        )

    def test_onboarding_question_schema_exposes_optional_hint(self) -> None:
        tools = Tools()

        tool = next(
            tool
            for tool in tools.to_model_tools(phase=Phase.ONBOARDING)
            if tool.name == "ask_onboarding_question"
        )
        hint = tool.parameters["properties"]["hint"]

        assert "hint" not in tool.parameters["required"]
        assert "Optional short note" in hint["description"]

    def test_onboarding_question_schema_exposes_optional_recommended_option(
        self,
    ) -> None:
        tools = Tools()

        tool = next(
            tool
            for tool in tools.to_model_tools(phase=Phase.ONBOARDING)
            if tool.name == "ask_onboarding_question"
        )
        properties = tool.parameters["properties"]

        assert "recommended_option" in properties
        assert "recommended_option" not in tool.parameters["required"]

    @pytest.mark.asyncio
    async def test_onboarding_question_threads_recommended_option(self) -> None:
        tools = Tools()

        result = await tools.execute(
            "ask_onboarding_question",
            {
                "question": "Welche Zeitspanne?",
                "options": ["Alle Jahrzehnte", "90er bis heute"],
                "recommended_option": "90er bis heute",
            },
            phase=Phase.ONBOARDING,
        )

        assert result.success is True
        assert result.input_request is not None
        assert result.input_request.recommended_option == "90er bis heute"

    def test_onboarding_question_schema_exposes_selection_mode_enum(self) -> None:
        tools = Tools()

        tool = next(
            tool
            for tool in tools.to_model_tools(phase=Phase.ONBOARDING)
            if tool.name == "ask_onboarding_question"
        )
        selection_mode = tool.parameters["properties"]["selection_mode"]

        assert selection_mode["default"] == "single_select"
        assert selection_mode["enum"] == ["single_select", "multi_select"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "options",
        [
            ["Solo"],
            [str(index) for index in range(5)],
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
            tool.name for tool in tools.to_model_tools(phase=Phase.ONBOARDING)
        }
        build_names = {tool.name for tool in tools.to_model_tools(phase=Phase.BUILD)}

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
            name="search_tracks",
            arguments='{"query": "abba"}',
        )

        parsed = tools.parse_args(tool_call)

        assert parsed == {"query": "abba"}

    def test_parse_args_returns_empty_dict_for_invalid_json(self) -> None:
        tools = Tools()
        tool_call = ToolCall(
            id="call-1",
            name="search_tracks",
            arguments="{not-json",
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
            'Added 1 track(s) to Hitster deck "Deck" (1 total).'
        )
        deck_draft = new_store.draft
        assert deck_draft is not None
        assert deck_draft.name == "Deck"
        assert deck_draft.tracks[0].title == "Take On Me"
        assert old_store.draft is None
        assert new_store.draft is not None
        assert new_store.draft.name == "Deck"


def _track(
    title: str,
    artist: str,
    spotify_uri: str,
    *,
    year: int | None = None,
    cover_url: str | None = None,
) -> DeckDraftTrack:
    return DeckDraftTrack(
        title=title,
        artist=artist,
        year=year,
        spotify_uri=spotify_uri,
        cover_url=cover_url,
    )


class _FakeSpotify(Spotify):
    def __init__(self, lookup_result: SpotifyTrackLookupResult) -> None:
        self.lookup_result = lookup_result

    async def search_tracks(self, params: SearchParams) -> SpotifyTrackLookupResult:
        return self.lookup_result


class TestWorkspaceDraftPlaylistTool:
    def test_registers_workspace_draft_tools_without_spotify_mutation_tools(
        self,
    ) -> None:
        tools = Tools(ToolContext(DeckStore()))

        tool_names = [tool.name for tool in tools.to_model_tools()]

        assert "create_deck" not in tool_names
        assert "add_deck_tracks" in tool_names
        assert "remove_deck_tracks" in tool_names
        assert "replace_deck_tracks" in tool_names
        assert "create_draft_playlist" not in tool_names
        assert "add_draft_playlist_tracks" not in tool_names
        assert "remove_draft_playlist_tracks" not in tool_names
        assert "replace_draft_playlist_tracks" not in tool_names
        assert "add_tracks_to_playlist" not in tool_names
        assert "remove_tracks_from_playlist" not in tool_names
        assert "clear_playlist" not in tool_names

    @pytest.mark.asyncio
    async def test_add_deck_tracks_rejects_non_track_uri_ref(
        self,
    ) -> None:
        store = DeckStore()
        tools = Tools(ToolContext(store))

        result = await tools.execute(
            "add_deck_tracks",
            {
                "status": "Tracks ins Deck legen",
                "tracks": [
                    {
                        "uri": "spotify:album:not-a-track",
                    }
                ],
            },
        )

        assert result.success is False
        assert "uri must start with 'spotify:track:'" in (result.error or "")
        assert store.draft is None
        assert store.drain_deck_draft_updates() == []

    @pytest.mark.asyncio
    async def test_search_tracks_caches_tracks_for_draft_refs(
        self,
    ) -> None:
        cached_track = _track(
            title="Take On Me",
            artist="a-ha",
            year=1985,
            spotify_uri="spotify:track:2WfaOiMkCvy7F5fcp2zZ8L",
            cover_url="https://i.scdn.co/image/take-on-me.jpg",
        )
        store = DeckStore()
        spotify = _FakeSpotify(
            SpotifyTrackLookupResult(
                content=(
                    "1. Take On Me - a-ha (1985) "
                    "uri=spotify:track:2WfaOiMkCvy7F5fcp2zZ8L"
                ),
                tracks=[cached_track],
            )
        )
        tools = Tools(ToolContext(store, spotify))

        search_result = await tools.execute(
            "search_tracks",
            {
                "query": "Take On Me",
                "status": "Suche nach 'Take On Me'",
            },
        )
        add_result = await tools.execute(
            "add_deck_tracks",
            {
                "status": "Tracks ins Deck legen",
                "tracks": [{"uri": "spotify:track:2WfaOiMkCvy7F5fcp2zZ8L"}],
            },
        )

        assert search_result.success is True
        assert add_result.success is True
        assert add_result.extracted_content == (
            'Added 1 track(s) to Hitster deck "Deck" (1 total).'
        )
        assert store.draft is not None
        assert store.draft.tracks[0].title == "Take On Me"

    @pytest.mark.asyncio
    async def test_add_remove_and_replace_deck_tracks_emit_diffs(
        self,
    ) -> None:
        store = DeckStore()
        store.cache_tracks(
            [
                _track(
                    title="Take On Me",
                    artist="a-ha",
                    year=1985,
                    spotify_uri="spotify:track:2WfaOiMkCvy7F5fcp2zZ8L",
                    cover_url="https://i.scdn.co/image/take-on-me.jpg",
                ),
                _track(
                    title="Billie Jean",
                    artist="Michael Jackson",
                    year=1982,
                    spotify_uri="spotify:track:5ChkMS8OtdzJeqyybCc9R5",
                    cover_url="https://i.scdn.co/image/billie-jean.jpg",
                ),
                _track(
                    title="Africa",
                    artist="Toto",
                    year=1982,
                    spotify_uri="spotify:track:2374M0fQpWi3dLnB54qaLX",
                    cover_url="https://i.scdn.co/image/africa.jpg",
                ),
            ]
        )
        tools = Tools(ToolContext(store))

        create_result = await tools.execute(
            "add_deck_tracks",
            {
                "status": "Tracks ins Deck legen",
                "tracks": [
                    {
                        "uri": "spotify:track:2WfaOiMkCvy7F5fcp2zZ8L",
                    }
                ],
            },
        )
        assert create_result.success is True
        assert create_result.extracted_content == (
            'Added 1 track(s) to Hitster deck "Deck" (1 total).'
        )
        playlist = store.draft
        assert playlist is not None
        store.drain_deck_draft_updates()

        added_playlist = await tools.execute(
            "add_deck_tracks",
            {
                "status": "Songs hinzufügen",
                "tracks": [
                    {
                        "uri": "spotify:track:5ChkMS8OtdzJeqyybCc9R5",
                    }
                ],
            },
        )
        add_update = store.drain_deck_draft_updates()[0]

        assert added_playlist.success is True
        assert added_playlist.extracted_content == (
            'Added 1 track(s) to Hitster deck "Deck" (2 total).'
        )
        assert store.draft is not None
        assert store.draft.tracks[-1].title == "Billie Jean"
        assert add_update.kind == "tracks_added"
        assert add_update.tracks[0].title == "Billie Jean"

        first_track_id = playlist.tracks[0].id
        await tools.execute(
            "replace_deck_tracks",
            {
                "status": "Song ersetzen",
                "replacements": [
                    {
                        "old_id": str(first_track_id),
                        "new_uri": "spotify:track:2374M0fQpWi3dLnB54qaLX",
                    }
                ],
            },
        )
        replace_update = store.drain_deck_draft_updates()[0]

        assert replace_update.kind == "tracks_replaced"
        assert replace_update.replacements[0].track_id == first_track_id
        assert replace_update.replacements[0].track.title == "Africa"

        assert store.draft is not None
        added_track_id = store.draft.tracks[-1].id
        await tools.execute(
            "remove_deck_tracks",
            {
                "status": "Song entfernen",
                "track_ids": [str(added_track_id)],
            },
        )
        remove_update = store.drain_deck_draft_updates()[0]

        assert remove_update.kind == "tracks_removed"
        assert remove_update.track_ids == [added_track_id]

    @pytest.mark.asyncio
    async def test_add_deck_tracks_creates_missing_draft_and_skips_duplicates(
        self,
    ) -> None:
        store = DeckStore()
        store.cache_tracks(
            [
                _track(
                    title="Take On Me",
                    artist="a-ha",
                    year=1985,
                    spotify_uri="spotify:track:2WfaOiMkCvy7F5fcp2zZ8L",
                ),
                _track(
                    title="Billie Jean",
                    artist="Michael Jackson",
                    year=1982,
                    spotify_uri="spotify:track:5ChkMS8OtdzJeqyybCc9R5",
                ),
            ]
        )
        tools = Tools(ToolContext(store))

        create_result = await tools.execute(
            "add_deck_tracks",
            {
                "status": "Songs ins Deck legen",
                "tracks": [
                    {"uri": "spotify:track:2WfaOiMkCvy7F5fcp2zZ8L"},
                    {"uri": "spotify:track:2WfaOiMkCvy7F5fcp2zZ8L"},
                ],
            },
        )
        create_update = store.drain_deck_draft_updates()[0]

        assert create_result.success is True
        assert create_result.extracted_content == (
            'Added 1 of 2 track(s) to Hitster deck "Deck" (1 total).'
            " The others were already in the deck."
        )
        assert store.draft is not None
        assert store.draft.name == "Deck"
        assert [track.title for track in store.draft.tracks] == ["Take On Me"]
        assert create_update.kind == "created"

        add_result = await tools.execute(
            "add_deck_tracks",
            {
                "status": "Songs ins Deck legen",
                "tracks": [
                    {"uri": "spotify:track:2WfaOiMkCvy7F5fcp2zZ8L"},
                    {"uri": "spotify:track:5ChkMS8OtdzJeqyybCc9R5"},
                    {"uri": "spotify:track:5ChkMS8OtdzJeqyybCc9R5"},
                ],
            },
        )
        add_updates = store.drain_deck_draft_updates()

        assert add_result.success is True
        assert add_result.extracted_content == (
            'Added 1 of 3 track(s) to Hitster deck "Deck" (2 total).'
            " The others were already in the deck."
        )
        assert store.draft is not None
        assert [track.title for track in store.draft.tracks] == [
            "Take On Me",
            "Billie Jean",
        ]
        assert len(add_updates) == 1
        assert add_updates[0].kind == "tracks_added"
        assert add_updates[0].tracks[0].title == "Billie Jean"

        duplicate_result = await tools.execute(
            "add_deck_tracks",
            {
                "status": "Songs ins Deck legen",
                "tracks": [
                    {"uri": "spotify:track:2WfaOiMkCvy7F5fcp2zZ8L"},
                    {"uri": "spotify:track:5ChkMS8OtdzJeqyybCc9R5"},
                ],
            },
        )

        assert duplicate_result.success is True
        assert store.drain_deck_draft_updates() == []

    def test_add_tracks_caps_at_max_tracks(self) -> None:
        existing = [
            _track(
                title="Take On Me",
                artist="a-ha",
                year=1985,
                spotify_uri="spotify:track:2WfaOiMkCvy7F5fcp2zZ8L",
            ),
            _track(
                title="Africa",
                artist="Toto",
                year=1982,
                spotify_uri="spotify:track:2374M0fQpWi3dLnB54qaLX",
            ),
        ]
        store = DeckStore(DeckDraft(name="Deck", tracks=existing), max_tracks=2)
        overflow = _track(
            title="Billie Jean",
            artist="Michael Jackson",
            year=1982,
            spotify_uri="spotify:track:5ChkMS8OtdzJeqyybCc9R5",
        )
        store.cache_tracks([overflow])

        draft = store.add_track_refs([TrackRef(uri=overflow.spotify_uri)])

        # Deck is already full: the overflow ref is dropped and no update emitted,
        # so the downstream session never exceeds its hard track limit.
        assert [track.title for track in draft.tracks] == ["Take On Me", "Africa"]
        assert store.drain_deck_draft_updates() == []

    @pytest.mark.asyncio
    async def test_add_deck_tracks_reports_when_deck_is_full(self) -> None:
        existing = _track(
            title="Take On Me",
            artist="a-ha",
            year=1985,
            spotify_uri="spotify:track:2WfaOiMkCvy7F5fcp2zZ8L",
        )
        store = DeckStore(DeckDraft(name="Deck", tracks=[existing]), max_tracks=1)
        store.cache_tracks(
            [
                _track(
                    title="Billie Jean",
                    artist="Michael Jackson",
                    year=1982,
                    spotify_uri="spotify:track:5ChkMS8OtdzJeqyybCc9R5",
                ),
            ]
        )
        tools = Tools(ToolContext(store))

        result = await tools.execute(
            "add_deck_tracks",
            {
                "status": "Songs ins Deck legen",
                "tracks": [{"uri": "spotify:track:5ChkMS8OtdzJeqyybCc9R5"}],
            },
        )

        assert result.success is True
        assert result.extracted_content == (
            'Added 0 of 1 track(s) to Hitster deck "Deck" (1 total).'
            " The deck is full (max 1); extra tracks were skipped."
        )
