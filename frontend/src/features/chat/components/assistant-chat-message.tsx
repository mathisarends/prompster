import { useSmoothStreamingText } from "@/features/chat/hooks/useSmoothStreamingText";
import { cn } from "@/shared/lib/utils";
import { MarkdownRenderer } from "@/shared/components/markdown-renderer";

import { ChatThinkingIndicator } from "./chat-thinking-indicator";
import { ToolCallAccordion, type ToolCallItem } from "./tool-call-sequence";

type AssistantChatMessageProps = {
  text: string;
  isStreaming?: boolean;
  toolCalls?: ToolCallItem[];
  attachedAbove?: boolean;
  className?: string;
};

export const AssistantChatMessage = ({
  text,
  isStreaming = false,
  toolCalls,
  attachedAbove = false,
  className,
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
        className,
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
