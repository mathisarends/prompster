from llmify import AssistantMessage, SystemMessage, ToolResultMessage, UserMessage
from llmify.messages import ToolCall

from agent.agent.messages import MessageManager


class TestMessageManager:
    def test_initializes_with_custom_system_prompt(self) -> None:
        manager = MessageManager(system_prompt="You are a helper")

        messages = manager.all()

        assert len(messages) == 1
        assert isinstance(messages[0], SystemMessage)
        assert messages[0].content == "You are a helper"

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

    def test_reset_keeps_only_system_message(self) -> None:
        manager = MessageManager(system_prompt="Prompt")
        manager.add_user("Hello")
        manager.add_assistant("Hi")

        manager.reset()

        messages = manager.all()
        assert len(messages) == 1
        assert isinstance(messages[0], SystemMessage)
        assert messages[0].content == "Prompt"
