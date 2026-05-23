import { Pencil, Star, Trash2 } from "lucide-react";

import { DropdownMenuItem } from "@/components/ui/dropdown-menu";

type SessionActionsMenuItemsProps = {
  isStarred: boolean;
  isTogglingStar?: boolean;
  onToggleStar: () => void;
  onRename: () => void;
  onDelete: () => void;
};

const getToggleStarLabel = (options: {
  isStarred: boolean;
  isTogglingStar: boolean;
}) => {
  const { isStarred, isTogglingStar } = options;

  if (isTogglingStar) {
    return isStarred ? "Stern wird entfernt..." : "Stern wird gesetzt...";
  }

  return isStarred ? "Stern entfernen" : "Mit Stern markieren";
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
      <span>{getToggleStarLabel({ isStarred, isTogglingStar })}</span>
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
