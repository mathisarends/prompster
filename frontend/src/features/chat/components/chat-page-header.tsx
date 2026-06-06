import { useState } from "react";
import { ChevronDown, Sparkles } from "lucide-react";

import type { SessionResponse } from "@/api/generated/model";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/shared/ui/dropdown-menu";
import { SessionActionsMenuItems } from "@/features/sessions/components/session-actions-menu-items";
import {
  DeleteChatDialog,
  RenameChatDialog,
} from "@/features/sessions/components/sidebar-session-dialogs";
import { Skeleton } from "@/shared/ui/skeleton";
import { useSessionStarActions } from "@/features/sessions/hooks/useSessionStarActions";
import { cn } from "@/shared/lib/utils";

type ChatPageHeaderProps = {
  session?: SessionResponse;
  title?: string;
  isLoading?: boolean;
  isTitlePending?: boolean;
  className?: string;
  onSessionDeleted?: (sessionId: string) => void;
};

export const ChatPageHeader = ({
  session,
  title,
  isLoading = false,
  isTitlePending = false,
  className,
  onSessionDeleted,
}: ChatPageHeaderProps) => {
  const [renameOpen, setRenameOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const { toggleStar, isTogglingFor } = useSessionStarActions();
  const displayTitle = title ?? session?.title ?? "Neues Karten-Deck";
  const showTitleSkeleton = isLoading || isTitlePending;

  return (
    <>
      <header
        className={cn(
          "flex h-14 shrink-0 items-center justify-start bg-background/80 px-5 backdrop-blur-md sm:px-8",
          className,
        )}
      >
        <span className="inline-flex min-w-0 items-center gap-2.5 text-sm font-semibold text-foreground/85">
          <Sparkles className="size-3.5 shrink-0" />
          {showTitleSkeleton && !session ? (
            <Skeleton className="h-4 w-40" />
          ) : session ? (
            <DropdownMenu>
              <DropdownMenuTrigger
                aria-label="Chat-Aktionen oeffnen"
                className="group/title -mx-2 -my-1 inline-flex min-w-0 items-center gap-1.5 rounded-md px-2 py-1 text-sm font-semibold transition-colors hover:bg-accent/60 focus-visible:ring-2 focus-visible:ring-ring data-[state=open]:bg-accent/60"
              >
                {showTitleSkeleton ? (
                  <Skeleton className="h-4 w-40" />
                ) : (
                  <span className="truncate">{displayTitle}</span>
                )}
                {!showTitleSkeleton && (
                  <ChevronDown className="size-3.5 shrink-0 text-foreground/60 transition-transform group-data-[state=open]/title:rotate-180" />
                )}
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" side="bottom" sideOffset={6}>
                <SessionActionsMenuItems
                  isStarred={session.isStarred}
                  isTogglingStar={isTogglingFor(session.id)}
                  onToggleStar={() => toggleStar(session)}
                  onRename={() => setRenameOpen(true)}
                  onDelete={() => setDeleteOpen(true)}
                />
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <span className="truncate">{displayTitle}</span>
          )}
        </span>
      </header>

      <RenameChatDialog
        session={session ?? null}
        open={renameOpen}
        onOpenChange={setRenameOpen}
      />
      <DeleteChatDialog
        session={session ?? null}
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        onDeleted={onSessionDeleted}
      />
    </>
  );
};
