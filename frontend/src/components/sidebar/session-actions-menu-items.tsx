import { Pencil, Star, Trash2 } from "lucide-react";

import { DropdownMenuItem } from "@/components/ui/dropdown-menu";

type SessionActionsMenuItemsProps = {
  isStarred: boolean;
  isTogglingStar?: boolean;
  onToggleStar: () => void;
  onRename: () => void;
  onDelete: () => void;
};

export const SessionActionsMenuItems = ({
  isStarred,
  isTogglingStar = false,
  onToggleStar,
  onRename,
  onDelete,
}: SessionActionsMenuItemsProps) => (
  <>
    <DropdownMenuItem onClick={onToggleStar} disabled={isTogglingStar}>
      <Star className={isStarred ? "fill-current" : undefined} />
      <span>
        {isStarred
          ? isTogglingStar
            ? "Stern wird entfernt..."
            : "Stern entfernen"
          : isTogglingStar
            ? "Markiere..."
            : "Markieren"}
      </span>
    </DropdownMenuItem>
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
  </>
);
