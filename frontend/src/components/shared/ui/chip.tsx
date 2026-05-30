import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

type ChipProps = {
  label: string;
  icon: LucideIcon;
  active?: boolean;
  disabled?: boolean;
  onClick?: () => void;
};

export const Chip = ({
  label,
  icon: Icon,
  active = false,
  disabled = false,
  onClick,
}: ChipProps) => {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "flex items-center gap-1.5 rounded-full border border-border/60 bg-card/40 px-4 py-2 text-sm text-muted-foreground backdrop-blur-sm transition-colors hover:border-border hover:bg-card/70 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50",
        active && "border-border bg-card/80 text-foreground",
      )}
    >
      <Icon className="size-3.5" />
      {label}
    </button>
  );
};
