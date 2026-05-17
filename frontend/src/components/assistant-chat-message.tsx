import { LoaderCircle } from "lucide-react";

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
    <div className="flex max-w-[82%] flex-col gap-1.5 px-1 py-2">
      {text ? (
        <MarkdownRenderer
          content={text}
          className="text-sm text-muted-foreground sm:text-base"
        />
      ) : isStreaming ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground sm:text-base">
          <LoaderCircle className="size-4 animate-spin" />
          <span>Antwort wird erstellt...</span>
        </div>
      ) : null}
      {toolCalls && <ToolCallAccordion calls={toolCalls} />}
    </div>
  );
};
