import { MarkdownRenderer } from "./markdown-renderer";
import { ToolCallAccordion, type ToolCallItem } from "./tool-call-accordion";

type AssistantChatMessageProps = {
  text: string;
  toolCalls?: ToolCallItem[];
};

export const AssistantChatMessage = ({
  text,
  toolCalls,
}: AssistantChatMessageProps) => {
  return (
    <div className="flex max-w-[82%] flex-col gap-1.5 px-1 py-2">
      <MarkdownRenderer
        content={text}
        className="text-sm text-muted-foreground sm:text-base"
      />
      {toolCalls && <ToolCallAccordion calls={toolCalls} />}
    </div>
  );
};
