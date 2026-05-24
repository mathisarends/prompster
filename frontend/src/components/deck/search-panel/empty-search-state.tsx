import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

type EmptySearchStateProps = {
  icon: LucideIcon;
  text: string;
  spin?: boolean;
};

export const EmptySearchState = ({
  icon: Icon,
  text,
  spin,
}: EmptySearchStateProps) => (
  <div className="flex min-h-28 flex-col items-center justify-center gap-2 text-center text-sm text-muted-foreground">
    <Icon className={cn("size-4", spin ? "animate-spin" : null)} />
    <p>{text}</p>
  </div>
);
