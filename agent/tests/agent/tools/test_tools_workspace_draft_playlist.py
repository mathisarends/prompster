import pytest

from agent.tools import ToolContext, Tools
from agent.workspace import PlaylistDraft, WorkspaceStore


class TestWorkspaceDraftPlaylistTool:
    def test_registers_build_draft_playlist_without_spotify_mutation_tools(
        self,
    ) -> None:
        tools = Tools(ToolContext(WorkspaceStore()))

        tool_names = [schema["function"]["name"] for schema in tools.to_schema()]

        assert "build_draft_playlist" in tool_names
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
                "tracks": [
                    {
                        "title": "Take On Me",
                        "artist": "a-ha",
                        "year": 1985,
                        "spotify_uri": "spotify:track:2WfaOiMkCvy7F5fcp2zZ8L",
                    }
                ],
            },
        )

        assert isinstance(result, PlaylistDraft)
        assert result.name == "80er Party"
        assert result.tracks[0].title == "Take On Me"
        assert workspace_store.playlist_draft == result
        assert workspace_store.drain_playlist_draft_updates() == [result]

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
                "tracks": [
                    {
                        "title": "Not a Track",
                        "artist": "Nobody",
                        "spotify_uri": "spotify:album:not-a-track",
                    }
                ],
            },
        )

        assert isinstance(result, str)
        assert "spotify_uri must start with 'spotify:track:'" in result
        assert workspace_store.playlist_draft is None
        assert workspace_store.drain_playlist_draft_updates() == []
