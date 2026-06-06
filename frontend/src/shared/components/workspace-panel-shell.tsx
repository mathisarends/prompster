import type { ReactNode } from "react";
import { X } from "lucide-react";

import { Button } from "@/shared/ui/button";
import { cn } from "@/shared/lib/utils";

type ChatWorkspacePanelProps = {
  children: ReactNode;
  onClose?: () => void;
  header?: ReactNode;
  contentClassName?: string;
};

export const ChatWorkspacePanel = ({
  children,
  onClose,
  contentClassName,
}: ChatWorkspacePanelProps) => {
  return (
    <section className="relative flex h-full min-h-0 flex-col bg-[hsl(222_36%_7%)] text-foreground shadow-2xl shadow-black/30">
      <div className="flex shrink-0 items-center justify-between gap-3 px-5 pb-3">
        {onClose ? (
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            onClick={onClose}
            aria-label="Arbeitsfläche schließen"
            className="shrink-0 text-muted-foreground hover:bg-white/10 hover:text-foreground"
          >
            <X className="size-4" />
          </Button>
        ) : null}
      </div>

      <div
        className={cn(
          "flex min-h-0 flex-1 flex-col px-5 pb-5",
          contentClassName,
        )}
      >
        {children}
      </div>
    </section>
  );
};
