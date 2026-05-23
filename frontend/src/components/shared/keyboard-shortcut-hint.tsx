import type { ReactElement } from "react";

import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { PlatformShortcutKey } from "@/hooks/usePlatform";
import { usePlatform } from "@/hooks/usePlatform";
import { cn } from "@/lib/utils";

export type ShortcutKey = PlatformShortcutKey;

type KeyboardShortcutHintProps = {
  children: ReactElement;
  label: string;
  keys: ShortcutKey[];
  side?: "top" | "right" | "bottom" | "left";
  align?: "start" | "center" | "end";
  className?: string;
};

export const KeyboardShortcutHint = ({
  children,
  label,
  keys,
  side = "right",
  align = "center",
  className,
}: KeyboardShortcutHintProps) => {
  const { formatShortcutKey } = usePlatform();

  return (
    <TooltipProvider delay={0}>
      <Tooltip>
        <TooltipTrigger render={children} />
        <TooltipContent
          side={side}
          align={align}
          sideOffset={8}
          showArrow={false}
          className={cn(
            "gap-2 border border-sidebar-border bg-sidebar px-2.5 py-1.5 text-sidebar-foreground shadow-xl",
            className,
          )}
        >
          <span className="whitespace-nowrap text-xs font-medium">{label}</span>
          <span className="flex items-center gap-1">
            {keys.map((key, index) => (
              <kbd
                key={`${key}-${index}`}
                data-slot="kbd"
                className="min-w-5 rounded border border-sidebar-border bg-sidebar-accent px-1.5 py-0.5 text-center text-[10px] font-semibold leading-none text-sidebar-accent-foreground"
              >
                {formatShortcutKey(key)}
              </kbd>
            ))}
          </span>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
};
