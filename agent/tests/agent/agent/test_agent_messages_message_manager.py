from datetime import datetime, timezone

from llmify import AssistantMessage, SystemMessage, ToolResultMessage, UserMessage
from llmify.messages import ToolCall

from agent.agent.messages import MessageManager
from agent.agent.views import UserEvent
from agent.playlist import PlaylistDraft, PlaylistDraftTrack


class TestMessageManager:
    def test_initializes_with_custom_system_prompt(self) -> None:
        manager = MessageManager(system_prompt="You are a helper")

        messages = manager.all()

        assert len(messages) == 1
        assert isinstance(messages[0], SystemMessage)
        assert messages[0].content.startswith("You are a helper")
        assert "<created_playlist>" in messages[0].content
        assert "<history>" in messages[0].content

    def test_add_methods_append_expected_message_types(self) -> None:
        manager = MessageManager(system_prompt="Prompt")
        tool_call = ToolCall(
            id="call-1",
            function={"name": "search_tracks", "arguments": '{"query":"abba"}'},
        )

        manager.add_user("Find tracks")
        manager.add_assistant("Searching", tool_calls=[tool_call])
        manager.add_tool_result("call-1", "[]")

        messages = manager.all()

        assert len(messages) == 4
        assert isinstance(messages[1], UserMessage)
        assert isinstance(messages[2], AssistantMessage)
        assert isinstance(messages[3], ToolResultMessage)
        assert messages[2].tool_calls[0].id == "call-1"
        assert messages[3].tool_call_id == "call-1"
        assert '<message role="user">' in messages[0].content
        assert "Find tracks" in messages[0].content
        assert "Searching" in messages[0].content

    def test_reset_keeps_only_system_message(self) -> None:
        manager = MessageManager(system_prompt="Prompt")
        manager.add_user("Hello")
        manager.add_assistant("Hi")

        manager.reset()

        messages = manager.all()
        assert len(messages) == 1
        assert isinstance(messages[0], SystemMessage)
        assert messages[0].content.startswith("Prompt")

    def test_renders_created_playlist_context(self) -> None:
        playlist = PlaylistDraft(
            name="80er Party",
            tracks=[
                PlaylistDraftTrack(
                    title="Take On Me",
                    artist="a-ha",
                    year=1985,
                    spotify_uri="spotify:track:1",
                )
            ],
        )
        manager = MessageManager(
            system_prompt="Prompt",
            playlist_draft_provider=lambda: playlist,
        )

        content = manager.all()[0].content

        assert "<created_playlist>" in content
        assert "<exists>true</exists>" in content
        assert "<name>80er Party</name>" in content
        assert "<track_count>1</track_count>" in content
        assert (
            f'<track index="1" id="{playlist.tracks[0].id}" pinned="false">'
            "a-ha - Take On Me (1985)</track>"
        ) in content

    def test_renders_user_events_context(self) -> None:
        manager = MessageManager(
            system_prompt="Prompt",
            user_events_provider=lambda: [
                UserEvent(
                    type="track_removed",
                    track_title="Umbrella",
                    track_artist="Rihanna",
                    occurred_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                )
            ],
        )

        content = manager.all()[0].content

        assert "<user_events>" in content
        assert "<exists>true</exists>" in content
        assert "<event_count>1</event_count>" in content
        assert (
            '<event index="1" type="track_removed" at="2026-01-01T00:00:00+00:00">'
            "Rihanna - Umbrella</event>"
        ) in content

    def test_renders_user_events_inside_history_timeline(self) -> None:
        manager = MessageManager(
            system_prompt="Prompt",
            user_events_provider=lambda: [
                UserEvent(
                    type="track_removed",
                    track_title="Umbrella",
                    track_artist="Rihanna",
                    occurred_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                    history_index=1,
                )
            ],
        )
        manager.add_user("Bitte mach die Playlist kürzer")
        manager.add_assistant("Klar, ich nehme ein paar Songs raus")

        content = manager.all()[0].content

        assert "<history>" in content
        assert '<message role="user">' in content
        assert '<message role="assistant">' in content
        history_fragment = (
            "<history>\n"
            '<message role="user">\n'
            "Bitte mach die Playlist kürzer\n"
            "</message>\n"
            '<event type="track_removed" at="2026-01-01T00:00:00+00:00">Rihanna - Umbrella</event>\n'
            '<message role="assistant">\n'
            "Klar, ich nehme ein paar Songs raus\n"
            "</message>\n"
            "</history>"
        )
        assert history_fragment in content
