import { ArrowUp, LoaderCircle, Square } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type SendButtonSize = "icon-xs" | "icon-sm" | "icon" | "icon-lg";

type SendButtonProps = {
  onClick: () => void;
  disabled?: boolean;
  isLoading?: boolean;
  isStopMode?: boolean;
  isStopping?: boolean;
  ariaLabel?: string;
  size?: SendButtonSize;
  className?: string;
};

export const SendButton = ({
  onClick,
  disabled = false,
  isLoading = false,
  isStopMode = false,
  isStopping = false,
  ariaLabel = "Nachricht senden",
  size = "icon",
  className,
}: SendButtonProps) => (
  <Button
    type="button"
    size={size}
    onClick={onClick}
    disabled={disabled || isStopping || (isLoading && !isStopMode)}
    aria-label={ariaLabel}
    className={cn(
      isStopMode &&
        "border-white/15 bg-white/10 text-foreground hover:bg-white/15",
      className,
    )}
  >
    {isStopMode ? (
      <Square
        className={cn(
          "fill-white text-white",
          size === "icon-xs" ? "size-3" : "size-4",
        )}
      />
    ) : isLoading ? (
      <LoaderCircle
        className={cn(
          "animate-spin text-white",
          size === "icon-xs" ? "size-3" : "size-4",
        )}
      />
    ) : (
      <ArrowUp
        className={cn("text-white", size === "icon-xs" ? "size-3" : "size-4")}
      />
    )}
  </Button>
);
