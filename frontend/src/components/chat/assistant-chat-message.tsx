import { useSmoothStreamingText } from "@/hooks/useSmoothStreamingText";
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
  const displayedText = useSmoothStreamingText(text, { isStreaming });
  // Keep the streaming caret alive until the smooth reveal has caught up, even
  // if the server already sent everything and flipped isStreaming off.
  const isRevealing = isStreaming || displayedText.length < text.length;

  return (
    <div
      className={cn(
        "chat-assistant-message flex max-w-[82%] flex-col gap-1.5 px-1 py-2",
        attachedAbove && "-mt-4 pt-0",
      )}
    >
      {displayedText ? (
        <MarkdownRenderer
          content={displayedText}
          className={cn("chat-assistant-prose", isRevealing && "is-streaming")}
        />
      ) : isStreaming ? (
        <ChatThinkingIndicator />
      ) : null}
      {toolCalls && <ToolCallAccordion calls={toolCalls} />}
    </div>
  );
};
