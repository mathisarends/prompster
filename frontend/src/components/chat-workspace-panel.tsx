import type { ReactNode } from "react";
import { X } from "lucide-react";

import { Button } from "@/components/ui/button";

type ChatWorkspacePanelProps = {
  children: ReactNode;
  onClose: () => void;
};

export const ChatWorkspacePanel = ({
  children,
  onClose,
}: ChatWorkspacePanelProps) => {
  return (
    <section className="relative flex h-full min-h-0 flex-col bg-[hsl(222_36%_7%)] text-foreground shadow-2xl shadow-black/30">
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        onClick={onClose}
        aria-label="Arbeitsfläche schließen"
        className="absolute right-5 top-4 z-10 shrink-0 text-muted-foreground hover:bg-white/10 hover:text-foreground"
      >
        <X className="size-4" />
      </Button>

      <div className="prompster-scrollbar flex min-h-0 flex-1 flex-col overflow-y-auto px-5 pb-5 pt-4">
        {children}
      </div>
    </section>
  );
};
