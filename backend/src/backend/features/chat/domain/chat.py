from datetime import datetime
from uuid import UUID

from backend.features.chat.domain.views import ChatMessage, MessageRole, ToolCall
from backend.shared.ddd import Aggregate


class Chat(Aggregate):
    def __init__(
        self,
        title: str,
        messages: list[ChatMessage],
        system_prompt: str | None = None,
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        self.title = title
        self.messages = messages
        self.system_prompt = system_prompt

    def add_user_message(self, content: str) -> ChatMessage:
        self._assert_no_pending_tool_calls()
        message = ChatMessage(role=MessageRole.USER, content=content)
        self.messages.append(message)
        return message

    def add_assistant_message(
        self, content: str, tool_calls: list[ToolCall] | None = None
    ) -> ChatMessage:
        message = ChatMessage(
            role=MessageRole.ASSISTANT, content=content, tool_calls=tool_calls
        )
        self.messages.append(message)
        return message

    def add_tool_result(self, tool_call_id: str, content: str) -> ChatMessage:
        self._assert_has_pending_tool_call(tool_call_id)
        message = ChatMessage(
            role=MessageRole.TOOL, content=content, tool_call_id=tool_call_id
        )
        self.messages.append(message)
        return message

    # TODO: add method for building more context:

    def _assert_no_pending_tool_calls(self) -> None:
        if self.messages and self.messages[-1].role == MessageRole.ASSISTANT:
            if self.messages[-1].tool_calls:
                raise ValueError(
                    "Cannot add user message while tool calls are pending."
                )

    def _assert_has_pending_tool_call(self, tool_call_id: str) -> None:
        pending_ids = {
            tc.id for m in self.messages if m.tool_calls for tc in m.tool_calls
        }
        resolved_ids = {m.tool_call_id for m in self.messages if m.tool_call_id}
        if tool_call_id not in (pending_ids - resolved_ids):
            raise ValueError(f"No pending tool call with id {tool_call_id!r}.")
