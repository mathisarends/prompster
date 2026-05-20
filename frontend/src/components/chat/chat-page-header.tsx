import { Sparkles } from "lucide-react";

import { cn } from "@/lib/utils";

type ChatPageHeaderProps = {
  title?: string;
  className?: string;
};

export const ChatPageHeader = ({
  title = "Neues Karten-Deck",
  className,
}: ChatPageHeaderProps) => {
  return (
    <header
      className={cn(
        "flex h-14 shrink-0 items-center justify-start bg-background/80 px-5 backdrop-blur-md sm:px-8",
        className,
      )}
    >
      <span className="inline-flex min-w-0 items-center gap-2.5 text-sm font-semibold text-foreground/85">
        <Sparkles className="size-3.5" />
        <span className="truncate">{title}</span>
      </span>
    </header>
  );
};
