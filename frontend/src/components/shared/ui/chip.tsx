import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

type ChipProps = {
  label: string;
  icon?: LucideIcon;
  active?: boolean;
  activeClassName?: string;
  className?: string;
  disabled?: boolean;
  onClick?: () => void;
};

export const Chip = ({
  label,
  icon: Icon,
  active = false,
  activeClassName,
  className,
  disabled = false,
  onClick,
}: ChipProps) => {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "flex items-center gap-1.5 rounded-full border border-border/60 bg-card/40 px-4 py-2 text-sm text-muted-foreground backdrop-blur-sm transition-all hover:border-border hover:bg-card/70 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring active:translate-y-px disabled:pointer-events-none disabled:opacity-50",
        active &&
          (activeClassName ?? "border-border bg-card/80 text-foreground"),
        className,
      )}
    >
      {Icon ? <Icon className="size-3.5 shrink-0" /> : null}
      {label}
    </button>
  );
};
