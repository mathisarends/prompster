import { useState } from "react";
import { MoreVertical } from "lucide-react";

import type { SessionSummaryResponse } from "@/api/generated/model";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { SessionActionsMenuItems } from "@/components/sidebar/session-actions-menu-items";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

type SidebarSessionItemProps = {
  session: SessionSummaryResponse;
  isActive: boolean;
  onSelect: () => void;
  onToggleStar: () => void;
  onRename: () => void;
  onDelete: () => void;
  isTogglingStar?: boolean;
};

export const SidebarSessionItem = ({
  session,
  isActive,
  onSelect,
  onToggleStar,
  onRename,
  onDelete,
  isTogglingStar = false,
}: SidebarSessionItemProps) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const shouldPinMenuButton = isActive || menuOpen;
  const hasTitle = Boolean(session.title.trim());
  const actionLabel = hasTitle
    ? `Aktionen fuer ${session.title}`
    : "Chat-Aktionen oeffnen";

  return (
    <li className="group/session relative">
      <button
        type="button"
        onClick={onSelect}
        className={cn(
          "flex w-full items-center rounded-md py-1.5 pl-2 pr-9 text-left text-sm transition-colors",
          isActive
            ? "bg-sidebar-accent text-sidebar-accent-foreground"
            : "text-sidebar-foreground/80 hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
        )}
      >
        {hasTitle ? (
          <span className="min-w-0 flex-1 truncate">{session.title}</span>
        ) : (
          <Skeleton className="h-3.5 w-32" />
        )}
      </button>

      <DropdownMenu open={menuOpen} onOpenChange={setMenuOpen}>
        <DropdownMenuTrigger
          aria-label={actionLabel}
          className={cn(
            "absolute right-1 top-1/2 grid size-7 -translate-y-1/2 place-items-center rounded-md text-sidebar-foreground/70 transition-opacity hover:bg-sidebar-accent hover:text-sidebar-accent-foreground focus-visible:opacity-100 focus-visible:ring-2 focus-visible:ring-sidebar-ring",
            "opacity-0 group-hover/session:opacity-100",
            shouldPinMenuButton && "opacity-100",
          )}
        >
          <MoreVertical className="size-4" />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" side="bottom" sideOffset={4}>
          <SessionActionsMenuItems
            isStarred={session.isStarred}
            isTogglingStar={isTogglingStar}
            onToggleStar={onToggleStar}
            onRename={onRename}
            onDelete={onDelete}
          />
        </DropdownMenuContent>
      </DropdownMenu>
    </li>
  );
};
