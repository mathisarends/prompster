import { useState } from "react";
import { MoreVertical, Pencil, Trash2 } from "lucide-react";

import type { SessionSummaryResponse } from "@/api/generated/model";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

type SidebarSessionItemProps = {
  session: SessionSummaryResponse;
  isActive: boolean;
  onSelect: () => void;
  onRename: () => void;
  onDelete: () => void;
};

export const SidebarSessionItem = ({
  session,
  isActive,
  onSelect,
  onRename,
  onDelete,
}: SidebarSessionItemProps) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const shouldPinMenuButton = isActive || menuOpen;

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
        <span className="min-w-0 flex-1 truncate">{session.title}</span>
      </button>

      <DropdownMenu open={menuOpen} onOpenChange={setMenuOpen}>
        <DropdownMenuTrigger
          aria-label={`Aktionen fuer ${session.title}`}
          className={cn(
            "absolute right-1 top-1/2 grid size-7 -translate-y-1/2 place-items-center rounded-md text-sidebar-foreground/70 transition-opacity hover:bg-sidebar-accent hover:text-sidebar-accent-foreground focus-visible:opacity-100 focus-visible:ring-2 focus-visible:ring-sidebar-ring",
            "opacity-0 group-hover/session:opacity-100",
            shouldPinMenuButton && "opacity-100",
          )}
        >
          <MoreVertical className="size-4" />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" side="bottom" sideOffset={4}>
          <DropdownMenuItem onClick={onRename}>
            <Pencil />
            <span>Umbenennen</span>
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={onDelete}
            className="text-destructive data-highlighted:bg-destructive/10 data-highlighted:text-destructive"
          >
            <Trash2 />
            <span>Löschen</span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </li>
  );
};
