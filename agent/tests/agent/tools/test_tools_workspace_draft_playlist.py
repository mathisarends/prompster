import pytest

from agent.tools import ToolContext, Tools
from agent.workspace import PlaylistDraft, WorkspaceStore


class TestWorkspaceDraftPlaylistTool:
    def test_registers_build_draft_playlist_without_spotify_mutation_tools(
        self,
    ) -> None:
        tools = Tools(ToolContext(WorkspaceStore()))

        tool_names = [schema["function"]["name"] for schema in tools.to_schema()]

        assert "create_draft_playlist" in tool_names
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
        tools = Tools(ToolContext(workspace_store))

        result = await tools.execute(
            "build_draft_playlist",
            {
                "name": "80er Party",
                "status": "Playlist-Entwurf bauen: '80er Party'",
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

        assert isinstance(result, PlaylistDraft)
        assert result.name == "80er Party"
        assert result.tracks[0].title == "Take On Me"
        assert result.tracks[0].cover_url == "https://i.scdn.co/image/take-on-me.jpg"
        assert workspace_store.playlist_draft == result
        updates = workspace_store.drain_playlist_draft_updates()
        assert len(updates) == 1
        assert updates[0].kind == "created"
        assert updates[0].playlist_draft == result

    @pytest.mark.asyncio
    async def test_build_draft_playlist_rejects_non_track_spotify_uri(
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
                        "title": "Not a Track",
                        "artist": "Nobody",
                        "spotify_uri": "spotify:album:not-a-track",
                        "cover_url": "https://i.scdn.co/image/whatever.jpg",
                    }
                ],
            },
        )

        assert isinstance(result, str)
        assert "spotify_uri must start with 'spotify:track:'" in result
        assert workspace_store.playlist_draft is None
        assert workspace_store.drain_playlist_draft_updates() == []

    @pytest.mark.asyncio
    async def test_add_remove_and_replace_draft_playlist_tracks_emit_diffs(
        self,
    ) -> None:
        workspace_store = WorkspaceStore()
        tools = Tools(ToolContext(workspace_store))

        playlist = await tools.execute(
            "create_draft_playlist",
            {
                "name": "80er Party",
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
        workspace_store.drain_playlist_draft_updates()

        added_playlist = await tools.execute(
            "add_draft_playlist_tracks",
            {
                "status": "Songs hinzufügen",
                "tracks": [
                    {
                        "title": "Billie Jean",
                        "artist": "Michael Jackson",
                        "year": 1982,
                        "spotify_uri": "spotify:track:5ChkMS8OtdzJeqyybCc9R5",
                        "cover_url": "https://i.scdn.co/image/billie-jean.jpg",
                    }
                ],
            },
        )
        add_update = workspace_store.drain_playlist_draft_updates()[0]

        assert added_playlist.tracks[-1].title == "Billie Jean"
        assert add_update.kind == "tracks_added"
        assert add_update.tracks[0].title == "Billie Jean"

        first_track_id = playlist.tracks[0].id
        await tools.execute(
            "replace_draft_playlist_tracks",
            {
                "status": "Song ersetzen",
                "replacements": [
                    {
                        "track_id": str(first_track_id),
                        "track": {
                            "title": "Africa",
                            "artist": "Toto",
                            "year": 1982,
                            "spotify_uri": "spotify:track:2374M0fQpWi3dLnB54qaLX",
                            "cover_url": "https://i.scdn.co/image/africa.jpg",
                        },
                    }
                ],
            },
        )
        replace_update = workspace_store.drain_playlist_draft_updates()[0]

        assert replace_update.kind == "tracks_replaced"
        assert replace_update.replacements[0].track_id == first_track_id
        assert replace_update.replacements[0].track.title == "Africa"

        added_track_id = added_playlist.tracks[-1].id
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
