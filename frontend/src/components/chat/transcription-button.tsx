import { AudioLines, LoaderCircle, Square } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

type TranscriptionButtonProps = {
  isRecording: boolean;
  isStarting: boolean;
  disabled?: boolean;
  onClick: () => void;
  className?: string;
  startTooltip?: string;
  stopTooltip?: string;
};

export const TranscriptionButton = ({
  isRecording,
  isStarting,
  disabled = false,
  onClick,
  className,
  startTooltip = "Sprachmodus verwenden",
  stopTooltip = "Transkription abbrechen",
}: TranscriptionButtonProps) => {
  const isBusy = isRecording || isStarting;

  return (
    <TooltipProvider delay={80}>
      <Tooltip>
        <TooltipTrigger
          render={
            <Button
              type="button"
              size="icon"
              variant="secondary"
              onClick={onClick}
              disabled={disabled}
              aria-label={
                isBusy ? "Spracheingabe beenden" : "Spracheingabe starten"
              }
              className={cn(
                "border",
                isBusy
                  ? "border-destructive/50 bg-destructive text-white hover:bg-destructive/90"
                  : "border-white/10 bg-slate-900/85 text-white shadow-sm shadow-black/35 hover:bg-slate-800/90 dark:bg-slate-800/85 dark:hover:bg-slate-700/90",
                className,
              )}
            >
              {isStarting ? (
                <LoaderCircle className="size-4 animate-spin text-white" />
              ) : isRecording ? (
                <Square className="size-3.5 fill-current text-white" />
              ) : (
                <AudioLines className="size-4 text-white" />
              )}
            </Button>
          }
        />
        <TooltipContent side="top" sideOffset={8} showArrow={false}>
          {isBusy ? stopTooltip : startTooltip}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
};
