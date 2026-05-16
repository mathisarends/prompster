type AssistantChatMessageProps = {
  text: string;
};

export const AssistantChatMessage = ({ text }: AssistantChatMessageProps) => {
  return (
    <div className="flex max-w-[82%] flex-col gap-1.5 px-1 py-2">
      <div className="text-sm leading-relaxed text-muted-foreground sm:text-base">
        {text}
      </div>
    </div>
  );
};
