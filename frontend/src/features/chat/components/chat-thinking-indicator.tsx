import { cn } from "@/shared/lib/utils";

type ChatThinkingIndicatorProps = {
  className?: string;
};

export const ChatThinkingIndicator = ({
  className,
}: ChatThinkingIndicatorProps) => (
  <div
    className={cn(
      "chat-thinking-dots flex items-center gap-1.5 py-1",
      className,
    )}
    aria-label="Antwort wird erstellt"
    role="status"
  >
    <span className="chat-thinking-dot" />
    <span className="chat-thinking-dot" />
    <span className="chat-thinking-dot" />
  </div>
);
