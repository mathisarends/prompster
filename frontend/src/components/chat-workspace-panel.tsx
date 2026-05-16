import type { ReactNode } from "react";
import { PanelRightClose } from "lucide-react";

import { Button } from "@/components/ui/button";

type ChatWorkspacePanelProps = {
  title: string;
  children: ReactNode;
  onClose: () => void;
};

export const ChatWorkspacePanel = ({
  title,
  children,
  onClose,
}: ChatWorkspacePanelProps) => {
  return (
    <section className="flex h-full min-h-0 flex-col bg-[hsl(222_36%_7%)] text-foreground shadow-2xl shadow-black/30">
      <div className="flex items-center justify-between gap-4 px-5 py-4">
        <h2 className="min-w-0 truncate text-base font-semibold">{title}</h2>
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          onClick={onClose}
          aria-label="Arbeitsfläche schließen"
          className="shrink-0 text-muted-foreground hover:bg-white/10 hover:text-foreground"
        >
          <PanelRightClose className="size-4" />
        </Button>
      </div>

      <div className="prompster-scrollbar flex min-h-0 flex-1 flex-col overflow-y-auto px-5 pb-5">
        {children}
      </div>
    </section>
  );
};
