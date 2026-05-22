import { cn } from "@/lib/utils";

import { MarkdownRenderer } from "./markdown-renderer";
import { ToolCallAccordion, type ToolCallItem } from "./tool-call-accordion";

type AssistantChatMessageProps = {
  text: string;
  isStreaming?: boolean;
  toolCalls?: ToolCallItem[];
};

export const AssistantChatMessage = ({
  text,
  isStreaming = false,
  toolCalls,
}: AssistantChatMessageProps) => {
  return (
    <div className="chat-assistant-message flex max-w-[82%] flex-col gap-1.5 px-1 py-2">
      {text ? (
        <MarkdownRenderer
          content={text}
          className={cn("chat-assistant-prose", isStreaming && "is-streaming")}
        />
      ) : isStreaming ? (
        <div
          className="chat-thinking-dots flex items-center gap-1.5 py-1"
          aria-label="Antwort wird erstellt"
          role="status"
        >
          <span className="chat-thinking-dot" />
          <span className="chat-thinking-dot" />
          <span className="chat-thinking-dot" />
        </div>
      ) : null}
      {toolCalls && <ToolCallAccordion calls={toolCalls} />}
    </div>
  );
};
