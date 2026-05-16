import { ArrowUp } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type SendButtonSize = "icon-xs" | "icon-sm" | "icon" | "icon-lg";

type SendButtonProps = {
  onClick: () => void;
  disabled?: boolean;
  ariaLabel?: string;
  size?: SendButtonSize;
  className?: string;
};

export const SendButton = ({
  onClick,
  disabled = false,
  ariaLabel = "Nachricht senden",
  size = "icon",
  className,
}: SendButtonProps) => (
  <Button
    type="button"
    size={size}
    onClick={onClick}
    disabled={disabled}
    aria-label={ariaLabel}
    className={className}
  >
    <ArrowUp className={cn("text-white", size === "icon-xs" ? "size-3" : "size-4")} />
  </Button>
);
