import { MarkdownRenderer } from "./markdown-renderer";

type AssistantChatMessageProps = {
  text: string;
};

export const AssistantChatMessage = ({ text }: AssistantChatMessageProps) => {
  return (
    <div className="flex max-w-[82%] flex-col gap-1.5 px-1 py-2">
      <MarkdownRenderer
        content={text}
        className="text-sm text-muted-foreground sm:text-base"
      />
    </div>
  );
};
