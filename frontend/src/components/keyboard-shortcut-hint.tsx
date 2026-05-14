import type { ReactElement } from "react";

import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

type ShortcutKey = "mod" | "shift" | "alt" | "enter" | "escape" | string;

type KeyboardShortcutHintProps = {
  children: ReactElement;
  label: string;
  keys: ShortcutKey[];
  side?: "top" | "right" | "bottom" | "left";
  align?: "start" | "center" | "end";
  className?: string;
};

const isApplePlatform = () => {
  if (typeof navigator === "undefined") {
    return false;
  }

  return /Mac|iPhone|iPad|iPod/.test(navigator.platform);
};

const formatShortcutKey = (key: ShortcutKey) => {
  const normalizedKey = key.toLocaleLowerCase();
  const applePlatform = isApplePlatform();

  if (normalizedKey === "mod") {
    return applePlatform ? "Cmd" : "Ctrl";
  }

  if (normalizedKey === "shift") {
    return "Shift";
  }

  if (normalizedKey === "alt") {
    return applePlatform ? "Option" : "Alt";
  }

  if (normalizedKey === "enter") {
    return "Enter";
  }

  if (normalizedKey === "escape") {
    return "Esc";
  }

  if (key.length === 1) {
    return key.toLocaleUpperCase();
  }

  return key;
};

export const KeyboardShortcutHint = ({
  children,
  label,
  keys,
  side = "right",
  align = "center",
  className,
}: KeyboardShortcutHintProps) => {
  return (
    <TooltipProvider delay={250}>
      <Tooltip>
        <TooltipTrigger render={children} />
        <TooltipContent
          side={side}
          align={align}
          sideOffset={8}
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
