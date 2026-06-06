import { AudioLines, LoaderCircle, Square } from "lucide-react";

import { Button } from "@/shared/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/shared/ui/tooltip";
import { cn } from "@/shared/lib/utils";

type TranscriptionButtonProps = {
  isRecording: boolean;
  isStarting: boolean;
  disabled?: boolean;
  onClick: () => void;
  className?: string;
};

export const TranscriptionButton = ({
  isRecording,
  isStarting,
  disabled = false,
  onClick,
  className,
}: TranscriptionButtonProps) => {
  const isActive = isRecording || isStarting;

  return (
    <TooltipProvider delay={80}>
      <Tooltip>
        <TooltipTrigger
          render={
            <Button
              type="button"
              size="icon"
              variant={isActive ? "default" : "ghost"}
              onClick={onClick}
              disabled={disabled}
              aria-label={
                isActive ? "Spracheingabe beenden" : "Spracheingabe starten"
              }
              className={cn(
                "relative rounded-full",
                isActive
                  ? "bg-foreground text-background hover:bg-foreground/90"
                  : "text-muted-foreground hover:text-foreground",
                className,
              )}
            >
              {isRecording && (
                <span className="pointer-events-none absolute inset-0 animate-ping rounded-full bg-foreground/25" />
              )}
              {isStarting ? (
                <LoaderCircle className="size-4 animate-spin" />
              ) : isRecording ? (
                <Square className="size-3.5 fill-current" />
              ) : (
                <AudioLines className="size-5" />
              )}
            </Button>
          }
        />
        <TooltipContent side="top" sideOffset={8} showArrow={false}>
          {isActive ? "Aufnahme beenden" : "Sprache zu Text"}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
};
