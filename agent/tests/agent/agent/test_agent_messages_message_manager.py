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

        assert len(messages) == 2
        assert isinstance(messages[0], SystemMessage)
        assert messages[0].content == "You are a helper"
        assert isinstance(messages[1], UserMessage)
        assert "<created_playlist>" in messages[1].content
        assert "<exists>false</exists>" in messages[1].content

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

        assert len(messages) == 5
        assert isinstance(messages[2], UserMessage)
        assert isinstance(messages[3], AssistantMessage)
        assert isinstance(messages[4], ToolResultMessage)
        assert messages[3].tool_calls[0].id == "call-1"
        assert messages[4].tool_call_id == "call-1"
        assert "Find tracks" in messages[2].content
        assert "Searching" in messages[3].content

    def test_reset_keeps_only_system_message(self) -> None:
        manager = MessageManager(system_prompt="Prompt")
        manager.add_user("Hello")
        manager.add_assistant("Hi")

        manager.reset()

        messages = manager.all()
        assert len(messages) == 2
        assert isinstance(messages[0], SystemMessage)
        assert messages[0].content == "Prompt"
        assert isinstance(messages[1], UserMessage)

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

        content = manager.all()[1].content

        assert "<created_playlist>" in content
        assert "<exists>true</exists>" in content
        assert "<name>80er Party</name>" in content
        assert "<track_count>1</track_count>" in content
        assert (
            f'<track index="1" id="{playlist.tracks[0].id}" pinned="false">'
            "a-ha - Take On Me (1985)</track>"
        ) in content

    def test_injects_user_events_as_synthetic_user_messages(self) -> None:
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

        messages = manager.all()

        assert len(messages) == 3
        assert isinstance(messages[2], UserMessage)
        assert (
            '<event type="track_removed" at="2026-01-01T00:00:00+00:00">'
            "Rihanna - Umbrella</event>"
        ) == messages[2].content

    def test_injects_user_events_inside_history_timeline(self) -> None:
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

        messages = manager.all()

        assert len(messages) == 5
        assert isinstance(messages[2], UserMessage)
        assert messages[2].content == "Bitte mach die Playlist kürzer"
        assert isinstance(messages[3], UserMessage)
        assert (
            messages[3].content
            == '<event type="track_removed" at="2026-01-01T00:00:00+00:00">Rihanna - Umbrella</event>'
        )
        assert isinstance(messages[4], AssistantMessage)
        assert messages[4].content == "Klar, ich nehme ein paar Songs raus"
