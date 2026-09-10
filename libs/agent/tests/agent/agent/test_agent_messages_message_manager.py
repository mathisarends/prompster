"""Low-level documentation tests for ``MessageManager``.

These tests describe — turn by turn — how MessageManager translates the
agent's internal state into the message list that is sent to the LLM. Each
test focuses on a single rendering rule so that the file can be read
top-to-bottom as a spec.

Key invariant: curation events (manual Hitster deck changes the user made
outside of the agent's tools) live inside the *same* ``UserMessage`` as the
user's text for that turn — mirroring the backend domain where
``UserMessage.user_curation_events`` is part of the user entity.
"""

from datetime import datetime, timezone

from llmify import AssistantMessage, SystemMessage, ToolResultMessage, UserMessage
from llmify.messages import ToolCall

from agent.messages import MessageManager, render_user_message_content
from agent.messages.rendering import (
    _render_user_events_block as render_user_events_block,
)
from agent.tools.views import Phase
from agent.views import UserCurationEventType, UserEvent
from agent.deck import DeckDraft, DeckDraftTrack


def _event(
    *,
    type: UserCurationEventType = UserCurationEventType.TRACK_REMOVED,
    title: str | None = "Umbrella",
    artist: str | None = "Rihanna",
    at: datetime = datetime(2026, 1, 1, tzinfo=timezone.utc),
) -> UserEvent:
    return UserEvent(
        type=type,
        track_title=title,
        track_artist=artist,
        occurred_at=at,
    )


class TestMessageManagerBaseline:
    """The minimal output: just the system prompt."""

    def test_fresh_manager_emits_only_the_system_message(self) -> None:
        manager = MessageManager(system_prompt="You are a helper")

        messages = manager.all()

        assert len(messages) == 1
        assert isinstance(messages[0], SystemMessage)
        assert messages[0].content == "You are a helper"

    def test_reset_drops_all_turns_but_keeps_system_prompt(self) -> None:
        manager = MessageManager(system_prompt="Prompt")
        manager.add_user("Hello")
        manager.add_assistant("Hi")

        manager.reset()

        messages = manager.all()
        assert [type(m) for m in messages] == [SystemMessage]
        assert messages[0].content == "Prompt"

    def test_onboarding_without_deck_context_emits_only_system_message(self) -> None:
        manager = MessageManager(
            system_prompt="Prompt",
            phase=Phase.ONBOARDING,
        )

        messages = manager.all()

        assert [type(m) for m in messages] == [SystemMessage]
        assert messages[0].content == "Prompt"


class TestMessageManagerConversationTurns:
    """Adding user/assistant/tool turns shows up as the matching LLM messages."""

    def test_add_user_appends_a_single_user_message(self) -> None:
        manager = MessageManager(system_prompt="Prompt")

        manager.add_user("Find tracks")

        messages = manager.all()
        assert [type(m) for m in messages] == [SystemMessage, UserMessage]
        assert messages[1].content == "Find tracks"

    def test_assistant_with_tool_call_then_tool_result_round_trip(self) -> None:
        manager = MessageManager(system_prompt="Prompt")
        tool_call = ToolCall(
            id="call-1",
            function={"name": "search_tracks", "arguments": '{"query":"abba"}'},
        )

        manager.add_user("Find tracks")
        manager.add_assistant("Searching", tool_calls=[tool_call])
        manager.add_tool_result("call-1", "[]")

        messages = manager.all()
        assert [type(m) for m in messages] == [
            SystemMessage,
            UserMessage,
            AssistantMessage,
            ToolResultMessage,
        ]
        assert messages[2].tool_calls[0].id == "call-1"
        assert messages[3].tool_call_id == "call-1"

    def test_compact_tool_results_elides_older_results_only(self) -> None:
        manager = MessageManager(system_prompt="Prompt")
        for index in range(6):
            manager.add_tool_result(f"call-{index}", f"verbose result {index}")

        compacted = manager.compact_tool_results(keep_last=2)

        messages = manager.all()
        tool_results = [
            message for message in messages if isinstance(message, ToolResultMessage)
        ]
        assert compacted == 4
        assert [message.tool_call_id for message in tool_results] == [
            "call-0",
            "call-1",
            "call-2",
            "call-3",
            "call-4",
            "call-5",
        ]
        assert all(
            message.content.startswith("[context-compacted]")
            for message in tool_results[:4]
        )
        assert [message.content for message in tool_results[4:]] == [
            "verbose result 4",
            "verbose result 5",
        ]

    def test_compact_tool_results_is_idempotent(self) -> None:
        manager = MessageManager(system_prompt="Prompt")
        for index in range(5):
            manager.add_tool_result(f"call-{index}", f"verbose result {index}")

        first = manager.compact_tool_results(keep_last=2)
        second = manager.compact_tool_results(keep_last=2)

        assert first == 3
        assert second == 0


class TestMessageManagerCurationEvents:
    """Curation events ride inside the same ``UserMessage`` they belong to.

    Mirrors the backend domain ``UserMessage.user_curation_events`` —
    the events are part of the user turn, not a separate turn.
    """

    def test_user_message_without_events_renders_only_the_text(self) -> None:
        manager = MessageManager(system_prompt="Prompt")

        manager.add_user("hallo")

        messages = manager.all()
        assert messages[1].content == "hallo"
        assert "<user_events>" not in messages[1].content

    def test_curation_events_prepend_a_user_events_block_to_the_same_message(
        self,
    ) -> None:
        manager = MessageManager(system_prompt="Prompt")

        manager.add_user(
            "mach die Playlist kürzer",
            curation_events=[_event()],
        )

        messages = manager.all()
        # Single UserMessage — events do NOT become a separate turn.
        assert [type(m) for m in messages] == [SystemMessage, UserMessage]
        assert messages[1].content == (
            "<user_events>\n"
            '<event type="track_removed" at="2026-01-01T00:00:00+00:00">'
            "Rihanna - Umbrella</event>\n"
            "</user_events>\n"
            "\n"
            "mach die Playlist kürzer"
        )

    def test_events_only_turn_renders_user_message_with_just_the_block(self) -> None:
        # Edge case: a turn carries curation events but no user text.
        # Still a single UserMessage so the LLM sees the manual changes in order.
        manager = MessageManager(system_prompt="Prompt")

        manager.add_user("", curation_events=[_event()])

        messages = manager.all()
        assert [type(m) for m in messages] == [SystemMessage, UserMessage]
        assert messages[1].content == (
            "<user_events>\n"
            '<event type="track_removed" at="2026-01-01T00:00:00+00:00">'
            "Rihanna - Umbrella</event>\n"
            "</user_events>"
        )

    def test_multiple_events_share_one_block_in_input_order(self) -> None:
        manager = MessageManager(system_prompt="Prompt")
        first = _event(
            type=UserCurationEventType.TRACK_REMOVED,
            title="Umbrella",
            artist="Rihanna",
            at=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        )
        second = _event(
            type=UserCurationEventType.TRACK_ADDED,
            title="Take On Me",
            artist="a-ha",
            at=datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc),
        )

        manager.add_user("weiter", curation_events=[first, second])

        body = manager.all()[1].content
        assert body == (
            "<user_events>\n"
            '<event type="track_removed" at="2026-01-01T10:00:00+00:00">'
            "Rihanna - Umbrella</event>\n"
            '<event type="track_added" at="2026-01-01T11:00:00+00:00">'
            "a-ha - Take On Me</event>\n"
            "</user_events>\n"
            "\n"
            "weiter"
        )

    def test_event_attributes_and_label_are_html_escaped(self) -> None:
        manager = MessageManager(system_prompt="Prompt")

        manager.add_user(
            "ok",
            curation_events=[_event(title='Song "X" & Y', artist="A&B")],
        )

        body = manager.all()[1].content
        assert "A&amp;B - Song &quot;X&quot; &amp; Y" in body

    def test_events_do_not_leak_into_unrelated_turns(self) -> None:
        # Only the turn that received the events should carry the block.
        manager = MessageManager(system_prompt="Prompt")

        manager.add_user("erste runde")
        manager.add_assistant("ok")
        manager.add_user("zweite runde", curation_events=[_event()])
        manager.add_assistant("verstanden")

        messages = manager.all()
        assert messages[1].content == "erste runde"
        assert "<user_events>" not in messages[1].content
        assert "<user_events>" in messages[3].content
        assert messages[3].content.endswith("zweite runde")
        assert messages[4].content == "verstanden"


class TestMessageManagerDeckContext:
    """The current Hitster deck draft is injected as a confirmed context turn."""

    def test_draft_renders_as_user_then_assistant_understood(self) -> None:
        deck = DeckDraft(
            name="80er Party",
            tracks=[
                DeckDraftTrack(
                    title="Take On Me",
                    artist="a-ha",
                    year=1985,
                    spotify_uri="spotify:track:1",
                )
            ],
        )
        manager = MessageManager(
            system_prompt="Prompt",
            deck_draft_provider=lambda: deck,
        )

        messages = manager.all()

        # Sandwich pattern: UserMessage + AssistantMessage("Understood.")
        # avoids consecutive UserMessages and frames the draft as confirmed
        # context rather than an open question.
        assert [type(m) for m in messages] == [
            SystemMessage,
            UserMessage,
            AssistantMessage,
        ]
        assert messages[2].content == "Understood."
        assert (
            f'<created_deck id="{deck.id}" name="80er Party" '
            'track_count="1" max_tracks="75" remaining_tracks="74" '
        ).rstrip() + ">" in messages[1].content
        assert (
            f'<track id="{deck.tracks[0].id}" label="a-ha - Take On Me (1985)" />'
        ) in messages[1].content

    def test_no_draft_means_no_context_injection(self) -> None:
        manager = MessageManager(
            system_prompt="Prompt",
            deck_draft_provider=lambda: None,
        )
        manager.add_user("hi")

        messages = manager.all()
        assert [type(m) for m in messages] == [SystemMessage, UserMessage]


class TestRenderingHelpers:
    """Standalone helpers — the rendering format is documented here in one place
    so that callers (e.g. the backend session_runner) can produce the same shape
    when rebuilding history from persistent state."""

    def test_render_user_events_block_format(self) -> None:
        block = render_user_events_block([_event()])

        assert block == (
            "<user_events>\n"
            '<event type="track_removed" at="2026-01-01T00:00:00+00:00">'
            "Rihanna - Umbrella</event>\n"
            "</user_events>"
        )

    def test_render_user_message_content_without_events_passes_through(self) -> None:
        assert render_user_message_content("hi") == "hi"
        assert render_user_message_content("hi", None) == "hi"
        assert render_user_message_content("hi", []) == "hi"

    def test_render_user_message_content_prepends_block_before_text(self) -> None:
        content = render_user_message_content("weiter", [_event()])

        assert content.startswith("<user_events>\n")
        assert content.endswith("\n\nweiter")

    def test_render_user_message_content_emits_only_block_when_text_is_empty(
        self,
    ) -> None:
        content = render_user_message_content("", [_event()])

        assert content == render_user_events_block([_event()])
