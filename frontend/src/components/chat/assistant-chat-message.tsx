import { cn } from "@/lib/utils";

import { ChatThinkingIndicator } from "./chat-thinking-indicator";
import { MarkdownRenderer } from "./markdown-renderer";
import { ToolCallAccordion, type ToolCallItem } from "./tool-call-sequence";

type AssistantChatMessageProps = {
  text: string;
  isStreaming?: boolean;
  toolCalls?: ToolCallItem[];
  attachedAbove?: boolean;
};

export const AssistantChatMessage = ({
  text,
  isStreaming = false,
  toolCalls,
  attachedAbove = false,
}: AssistantChatMessageProps) => {
  return (
    <div
      className={cn(
        "chat-assistant-message flex max-w-[82%] flex-col gap-1.5 px-1 py-2",
        attachedAbove && "-mt-4 pt-0",
      )}
    >
      {text ? (
        <MarkdownRenderer
          content={text}
          className={cn("chat-assistant-prose", isStreaming && "is-streaming")}
        />
      ) : isStreaming ? (
        <ChatThinkingIndicator />
      ) : null}
      {toolCalls && <ToolCallAccordion calls={toolCalls} />}
    </div>
  );
};
