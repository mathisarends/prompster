import pytest

from agent.tools import ToolContext, Tools
from agent.tools.handler import Spotify
from agent.tools.handler.spotify import SpotifyTrackLookupResult
from agent.tools.views import SearchParams
from agent.workspace import (
    PlaylistDraft,
    PlaylistDraftToolResult,
    PlaylistDraftTrack,
    WorkspaceStore,
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
    def test_registers_build_draft_playlist_without_spotify_mutation_tools(
        self,
    ) -> None:
        tools = Tools(ToolContext(WorkspaceStore()))

        tool_names = [schema["function"]["name"] for schema in tools.to_schema()]

        assert "create_draft_playlist" not in tool_names
        assert "build_draft_playlist" in tool_names
        assert "add_draft_playlist_tracks" in tool_names
        assert "remove_draft_playlist_tracks" in tool_names
        assert "replace_draft_playlist_tracks" in tool_names
        assert "create_playlist" not in tool_names
        assert "add_tracks_to_playlist" not in tool_names
        assert "remove_tracks_from_playlist" not in tool_names
        assert "clear_playlist" not in tool_names

    @pytest.mark.asyncio
    async def test_build_draft_playlist_saves_and_returns_playlist_draft(
        self,
    ) -> None:
        workspace_store = WorkspaceStore()
        workspace_store.cache_tracks(
            [
                _track(
                    title="Take On Me",
                    artist="a-ha",
                    year=1985,
                    spotify_uri="spotify:track:2WfaOiMkCvy7F5fcp2zZ8L",
                    cover_url="https://i.scdn.co/image/take-on-me.jpg",
                )
            ]
        )
        tools = Tools(ToolContext(workspace_store))

        result = await tools.execute(
            "build_draft_playlist",
            {
                "name": "80er Party",
                "status": "Playlist-Entwurf bauen: '80er Party'",
                "tracks": [
                    {
                        "uri": "spotify:track:2WfaOiMkCvy7F5fcp2zZ8L",
                    }
                ],
            },
        )

        assert result.success is True
        tool_result = result.extracted_content
        assert isinstance(tool_result, PlaylistDraftToolResult)
        playlist = tool_result.playlist_draft
        assert isinstance(playlist, PlaylistDraft)
        assert tool_result.operations[0].operation == "build_draft_playlist"
        assert tool_result.operations[0].success is True
        assert playlist.name == "80er Party"
        assert playlist.tracks[0].title == "Take On Me"
        assert playlist.tracks[0].cover_url == "https://i.scdn.co/image/take-on-me.jpg"
        assert workspace_store.playlist_draft == playlist
        updates = workspace_store.drain_playlist_draft_updates()
        assert len(updates) == 1
        assert updates[0].kind == "created"
        assert updates[0].playlist_draft == playlist

    @pytest.mark.asyncio
    async def test_build_draft_playlist_rejects_non_track_uri_ref(
        self,
    ) -> None:
        workspace_store = WorkspaceStore()
        tools = Tools(ToolContext(workspace_store))

        result = await tools.execute(
            "build_draft_playlist",
            {
                "name": "Broken Draft",
                "status": "Playlist-Entwurf bauen",
                "tracks": [
                    {
                        "uri": "spotify:album:not-a-track",
                    }
                ],
            },
        )

        assert result.success is False
        assert "uri must start with 'spotify:track:'" in (result.error or "")
        assert workspace_store.playlist_draft is None
        assert workspace_store.drain_playlist_draft_updates() == []

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
        workspace_store = WorkspaceStore()
        spotify = _FakeSpotify(
            SpotifyTrackLookupResult(
                content=(
                    "1. Take On Me - a-ha (1985) "
                    "uri=spotify:track:2WfaOiMkCvy7F5fcp2zZ8L"
                ),
                tracks=[cached_track],
            )
        )
        tools = Tools(ToolContext(workspace_store, spotify))

        search_result = await tools.execute(
            "search_tracks",
            {
                "query": "Take On Me",
                "status": "Suche nach 'Take On Me'",
            },
        )
        build_result = await tools.execute(
            "build_draft_playlist",
            {
                "name": "80er Party",
                "status": "Playlist-Entwurf bauen",
                "tracks": [{"uri": "spotify:track:2WfaOiMkCvy7F5fcp2zZ8L"}],
            },
        )

        assert search_result.success is True
        assert build_result.success is True
        tool_result = build_result.extracted_content
        assert isinstance(tool_result, PlaylistDraftToolResult)
        assert tool_result.playlist_draft is not None
        assert tool_result.playlist_draft.tracks[0].title == "Take On Me"

    @pytest.mark.asyncio
    async def test_add_remove_and_replace_draft_playlist_tracks_emit_diffs(
        self,
    ) -> None:
        workspace_store = WorkspaceStore()
        workspace_store.cache_tracks(
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
        tools = Tools(ToolContext(workspace_store))

        create_result = await tools.execute(
            "build_draft_playlist",
            {
                "name": "80er Party",
                "status": "Playlist-Entwurf bauen",
                "tracks": [
                    {
                        "uri": "spotify:track:2WfaOiMkCvy7F5fcp2zZ8L",
                    }
                ],
            },
        )
        assert create_result.success is True
        create_tool_result = create_result.extracted_content
        assert isinstance(create_tool_result, PlaylistDraftToolResult)
        playlist = create_tool_result.playlist_draft
        assert playlist is not None
        workspace_store.drain_playlist_draft_updates()

        added_playlist = await tools.execute(
            "add_draft_playlist_tracks",
            {
                "status": "Songs hinzufügen",
                "tracks": [
                    {
                        "uri": "spotify:track:5ChkMS8OtdzJeqyybCc9R5",
                    }
                ],
            },
        )
        add_update = workspace_store.drain_playlist_draft_updates()[0]

        assert added_playlist.success is True
        added_tool_result = added_playlist.extracted_content
        assert isinstance(added_tool_result, PlaylistDraftToolResult)
        assert added_tool_result.playlist_draft is not None
        assert added_tool_result.playlist_draft.tracks[-1].title == "Billie Jean"
        assert add_update.kind == "tracks_added"
        assert add_update.tracks[0].title == "Billie Jean"

        first_track_id = playlist.tracks[0].id
        await tools.execute(
            "replace_draft_playlist_tracks",
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
        replace_update = workspace_store.drain_playlist_draft_updates()[0]

        assert replace_update.kind == "tracks_replaced"
        assert replace_update.replacements[0].track_id == first_track_id
        assert replace_update.replacements[0].track.title == "Africa"

        added_track_id = added_tool_result.playlist_draft.tracks[-1].id
        await tools.execute(
            "remove_draft_playlist_tracks",
            {
                "status": "Song entfernen",
                "track_ids": [str(added_track_id)],
            },
        )
        remove_update = workspace_store.drain_playlist_draft_updates()[0]

        assert remove_update.kind == "tracks_removed"
        assert remove_update.track_ids == [added_track_id]

    @pytest.mark.asyncio
    async def test_pinned_tracks_cannot_be_removed_or_replaced_and_survive_rebuild(
        self,
    ) -> None:
        workspace_store = WorkspaceStore()
        workspace_store.cache_tracks(
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
        tools = Tools(ToolContext(workspace_store))

        create_result = await tools.execute(
            "build_draft_playlist",
            {
                "name": "80er Party",
                "status": "Playlist-Entwurf bauen",
                "tracks": [
                    {
                        "uri": "spotify:track:2WfaOiMkCvy7F5fcp2zZ8L",
                        "pinned": True,
                    }
                ],
            },
        )
        assert create_result.success is True
        create_tool_result = create_result.extracted_content
        assert isinstance(create_tool_result, PlaylistDraftToolResult)
        playlist = create_tool_result.playlist_draft
        assert playlist is not None
        workspace_store.drain_playlist_draft_updates()
        pinned_track_id = playlist.tracks[0].id

        remove_result = await tools.execute(
            "remove_draft_playlist_tracks",
            {
                "status": "Song entfernen",
                "track_ids": [str(pinned_track_id)],
            },
        )
        replace_result = await tools.execute(
            "replace_draft_playlist_tracks",
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
        rebuild_result = await tools.execute(
            "build_draft_playlist",
            {
                "name": "80er Party",
                "status": "Playlist neu bauen",
                "tracks": [
                    {
                        "uri": "spotify:track:5ChkMS8OtdzJeqyybCc9R5",
                    }
                ],
            },
        )

        assert remove_result.success is False
        assert "pinned" in (remove_result.error or "")
        remove_tool_result = remove_result.extracted_content
        assert isinstance(remove_tool_result, PlaylistDraftToolResult)
        assert remove_tool_result.operations[0].success is False
        assert "pinned" in (remove_tool_result.operations[0].reason or "")
        assert replace_result.success is False
        assert "pinned" in (replace_result.error or "")
        replace_tool_result = replace_result.extracted_content
        assert isinstance(replace_tool_result, PlaylistDraftToolResult)
        assert replace_tool_result.operations[0].success is False
        assert "pinned" in (replace_tool_result.operations[0].reason or "")
        assert rebuild_result.success is True
        rebuild_tool_result = rebuild_result.extracted_content
        assert isinstance(rebuild_tool_result, PlaylistDraftToolResult)
        assert rebuild_tool_result.playlist_draft is not None
        assert rebuild_tool_result.playlist_draft.tracks[0] == playlist.tracks[0]
        assert workspace_store.playlist_draft == rebuild_tool_result.playlist_draft
        assert workspace_store.drain_playlist_draft_updates()[0].kind == "replaced"
