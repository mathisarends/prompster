import { ArrowUp, LoaderCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type SendButtonSize = "icon-xs" | "icon-sm" | "icon" | "icon-lg";

type SendButtonProps = {
  onClick: () => void;
  disabled?: boolean;
  isLoading?: boolean;
  ariaLabel?: string;
  size?: SendButtonSize;
  className?: string;
};

export const SendButton = ({
  onClick,
  disabled = false,
  isLoading = false,
  ariaLabel = "Nachricht senden",
  size = "icon",
  className,
}: SendButtonProps) => (
  <Button
    type="button"
    size={size}
    onClick={onClick}
    disabled={disabled || isLoading}
    aria-label={ariaLabel}
    className={className}
  >
    {isLoading ? (
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
