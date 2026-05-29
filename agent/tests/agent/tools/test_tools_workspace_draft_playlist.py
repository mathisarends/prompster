import pytest

from agent.tools import ToolContext, Tools
from agent.tools.handler import Spotify
from agent.tools.handler.spotify import SpotifyTrackLookupResult
from agent.tools.views import SearchParams
from agent.playlist import (
    PlaylistDraft,
    PlaylistDraftTrack,
    PlaylistDraftStore,
)


def _track(
    title: str,
    artist: str,
    spotify_uri: str,
    *,
    year: int | None = None,
    cover_url: str | None = None,
    is_pinned: bool = False,
) -> PlaylistDraftTrack:
    return PlaylistDraftTrack(
        title=title,
        artist=artist,
        year=year,
        spotify_uri=spotify_uri,
        cover_url=cover_url,
        is_pinned=is_pinned,
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
        tools = Tools(ToolContext(PlaylistDraftStore()))

        tool_names = [schema["function"]["name"] for schema in tools.to_schema()]

        assert "create_playlist" in tool_names
        assert "add_playlist_tracks" in tool_names
        assert "remove_playlist_tracks" in tool_names
        assert "replace_playlist_tracks" in tool_names
        assert "create_draft_playlist" not in tool_names
        assert "add_draft_playlist_tracks" not in tool_names
        assert "remove_draft_playlist_tracks" not in tool_names
        assert "replace_draft_playlist_tracks" not in tool_names
        assert "add_tracks_to_playlist" not in tool_names
        assert "remove_tracks_from_playlist" not in tool_names
        assert "clear_playlist" not in tool_names

    def test_create_playlist_schema_does_not_accept_tracks(self) -> None:
        tools = Tools(ToolContext(PlaylistDraftStore()))

        schema = next(
            schema
            for schema in tools.to_schema()
            if schema["function"]["name"] == "create_playlist"
        )

        properties = schema["function"]["parameters"]["properties"]
        assert "name" in properties
        assert "tracks" not in properties

    @pytest.mark.asyncio
    async def test_create_playlist_saves_empty_draft(
        self,
    ) -> None:
        store = PlaylistDraftStore()
        tools = Tools(ToolContext(store))

        result = await tools.execute(
            "create_playlist",
            {
                "name": "80er Party",
                "status": "Baue das 80er-Deck",
            },
        )

        assert result.success is True
        assert isinstance(result.extracted_content, str)
        assert result.extracted_content == 'Playlist "80er Party" created.'
        playlist = store.playlist_draft
        assert isinstance(playlist, PlaylistDraft)
        assert playlist.name == "80er Party"
        assert playlist.tracks == []
        assert store.playlist_draft == playlist
        updates = store.drain_playlist_draft_updates()
        assert len(updates) == 1
        assert updates[0].kind == "created"
        assert updates[0].playlist_draft == playlist

    @pytest.mark.asyncio
    async def test_create_playlist_rejects_existing_draft(
        self,
    ) -> None:
        store = PlaylistDraftStore(PlaylistDraft(name="Existing", tracks=[]))
        tools = Tools(ToolContext(store))

        result = await tools.execute(
            "create_playlist",
            {
                "name": "80er Party",
                "status": "Baue das 80er-Deck",
            },
        )

        assert result.success is False
        assert "already exists" in (result.error or "")
        assert store.playlist_draft is not None
        assert store.playlist_draft.name == "Existing"
        assert store.drain_playlist_draft_updates() == []

    @pytest.mark.asyncio
    async def test_add_playlist_tracks_rejects_non_track_uri_ref(
        self,
    ) -> None:
        store = PlaylistDraftStore()
        tools = Tools(ToolContext(store))

        result = await tools.execute(
            "add_playlist_tracks",
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
        assert store.playlist_draft is None
        assert store.drain_playlist_draft_updates() == []

    @pytest.mark.asyncio
    async def test_add_playlist_tracks_rejects_agent_pinned_flag(
        self,
    ) -> None:
        store = PlaylistDraftStore()
        tools = Tools(ToolContext(store))

        result = await tools.execute(
            "add_playlist_tracks",
            {
                "status": "Tracks ins Deck legen",
                "tracks": [
                    {
                        "uri": "spotify:track:2WfaOiMkCvy7F5fcp2zZ8L",
                        "pinned": True,
                    }
                ],
            },
        )

        assert result.success is False
        assert "pinned" in (result.error or "")
        assert store.playlist_draft is None
        assert store.drain_playlist_draft_updates() == []

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
        store = PlaylistDraftStore()
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
            "add_playlist_tracks",
            {
                "status": "Tracks ins Deck legen",
                "tracks": [{"uri": "spotify:track:2WfaOiMkCvy7F5fcp2zZ8L"}],
            },
        )

        assert search_result.success is True
        assert add_result.success is True
        assert add_result.extracted_content == (
            '1 track reference(s) processed for playlist "Playlist".'
        )
        assert store.playlist_draft is not None
        assert store.playlist_draft.tracks[0].title == "Take On Me"

    @pytest.mark.asyncio
    async def test_add_remove_and_replace_playlist_tracks_emit_diffs(
        self,
    ) -> None:
        store = PlaylistDraftStore()
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
            "add_playlist_tracks",
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
            '1 track reference(s) processed for playlist "Playlist".'
        )
        playlist = store.playlist_draft
        assert playlist is not None
        store.drain_playlist_draft_updates()

        added_playlist = await tools.execute(
            "add_playlist_tracks",
            {
                "status": "Songs hinzufügen",
                "tracks": [
                    {
                        "uri": "spotify:track:5ChkMS8OtdzJeqyybCc9R5",
                    }
                ],
            },
        )
        add_update = store.drain_playlist_draft_updates()[0]

        assert added_playlist.success is True
        assert added_playlist.extracted_content == (
            '1 track reference(s) processed for playlist "Playlist".'
        )
        assert store.playlist_draft is not None
        assert store.playlist_draft.tracks[-1].title == "Billie Jean"
        assert add_update.kind == "tracks_added"
        assert add_update.tracks[0].title == "Billie Jean"

        first_track_id = playlist.tracks[0].id
        await tools.execute(
            "replace_playlist_tracks",
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
        replace_update = store.drain_playlist_draft_updates()[0]

        assert replace_update.kind == "tracks_replaced"
        assert replace_update.replacements[0].track_id == first_track_id
        assert replace_update.replacements[0].track.title == "Africa"

        assert store.playlist_draft is not None
        added_track_id = store.playlist_draft.tracks[-1].id
        await tools.execute(
            "remove_playlist_tracks",
            {
                "status": "Song entfernen",
                "track_ids": [str(added_track_id)],
            },
        )
        remove_update = store.drain_playlist_draft_updates()[0]

        assert remove_update.kind == "tracks_removed"
        assert remove_update.track_ids == [added_track_id]

    @pytest.mark.asyncio
    async def test_add_playlist_tracks_creates_missing_draft_and_skips_duplicates(
        self,
    ) -> None:
        store = PlaylistDraftStore()
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
            "add_playlist_tracks",
            {
                "status": "Songs ins Deck legen",
                "tracks": [
                    {"uri": "spotify:track:2WfaOiMkCvy7F5fcp2zZ8L"},
                    {"uri": "spotify:track:2WfaOiMkCvy7F5fcp2zZ8L"},
                ],
            },
        )
        create_update = store.drain_playlist_draft_updates()[0]

        assert create_result.success is True
        assert create_result.extracted_content == (
            '2 track reference(s) processed for playlist "Playlist".'
        )
        assert store.playlist_draft is not None
        assert store.playlist_draft.name == "Playlist"
        assert [track.title for track in store.playlist_draft.tracks] == ["Take On Me"]
        assert create_update.kind == "created"

        add_result = await tools.execute(
            "add_playlist_tracks",
            {
                "status": "Songs ins Deck legen",
                "tracks": [
                    {"uri": "spotify:track:2WfaOiMkCvy7F5fcp2zZ8L"},
                    {"uri": "spotify:track:5ChkMS8OtdzJeqyybCc9R5"},
                    {"uri": "spotify:track:5ChkMS8OtdzJeqyybCc9R5"},
                ],
            },
        )
        add_updates = store.drain_playlist_draft_updates()

        assert add_result.success is True
        assert add_result.extracted_content == (
            '3 track reference(s) processed for playlist "Playlist".'
        )
        assert store.playlist_draft is not None
        assert [track.title for track in store.playlist_draft.tracks] == [
            "Take On Me",
            "Billie Jean",
        ]
        assert len(add_updates) == 1
        assert add_updates[0].kind == "tracks_added"
        assert add_updates[0].tracks[0].title == "Billie Jean"

        duplicate_result = await tools.execute(
            "add_playlist_tracks",
            {
                "status": "Songs ins Deck legen",
                "tracks": [
                    {"uri": "spotify:track:2WfaOiMkCvy7F5fcp2zZ8L"},
                    {"uri": "spotify:track:5ChkMS8OtdzJeqyybCc9R5"},
                ],
            },
        )

        assert duplicate_result.success is True
        assert store.drain_playlist_draft_updates() == []

    @pytest.mark.asyncio
    async def test_pinned_tracks_cannot_be_removed_or_replaced(
        self,
    ) -> None:
        pinned_track = _track(
            title="Take On Me",
            artist="a-ha",
            year=1985,
            spotify_uri="spotify:track:2WfaOiMkCvy7F5fcp2zZ8L",
            cover_url="https://i.scdn.co/image/take-on-me.jpg",
            is_pinned=True,
        )
        store = PlaylistDraftStore(
            PlaylistDraft(name="80er Party", tracks=[pinned_track])
        )
        store.cache_tracks(
            [
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
        pinned_track_id = pinned_track.id

        remove_result = await tools.execute(
            "remove_playlist_tracks",
            {
                "status": "Song entfernen",
                "track_ids": [str(pinned_track_id)],
            },
        )
        replace_result = await tools.execute(
            "replace_playlist_tracks",
            {
                "status": "Song ersetzen",
                "replacements": [
                    {
                        "old_id": str(pinned_track_id),
                        "new_uri": "spotify:track:2374M0fQpWi3dLnB54qaLX",
                    }
                ],
            },
        )
        assert remove_result.success is False
        assert "pinned" in (remove_result.error or "")
        assert remove_result.extracted_content == ""
        assert replace_result.success is False
        assert "pinned" in (replace_result.error or "")
        assert replace_result.extracted_content == ""
        assert store.playlist_draft is not None
        assert store.playlist_draft.tracks == [pinned_track]
        assert store.drain_playlist_draft_updates() == []
