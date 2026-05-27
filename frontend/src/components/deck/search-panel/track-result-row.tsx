import { Loader2, Pause, Play, Plus } from "lucide-react";

import type { SpotifyTrackResponse } from "@/api/generated/model";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

type TrackResultRowProps = {
  track: SpotifyTrackResponse;
  isAdding: boolean;
  disabled: boolean;
  isActive: boolean;
  isPlaying: boolean;
  previewDisabled?: boolean;
  onAdd: () => void;
  onTogglePreview?: () => void;
};

export const TrackResultRow = ({
  track,
  isAdding,
  disabled,
  isActive,
  isPlaying,
  previewDisabled = false,
  onAdd,
  onTogglePreview,
}: TrackResultRowProps) => {
  const isActivelyPlaying = isActive && isPlaying;
  const previewLabel = isActivelyPlaying
    ? `${track.title} pausieren`
    : `${track.title} anspielen`;

  return (
    <div
      className={cn(
        "group relative grid grid-cols-[minmax(0,1fr)_64px_36px] items-center gap-x-3 rounded-md px-2 py-2.5 transition-colors",
        isActive ? "bg-white/[0.025]" : "hover:bg-white/[0.035]",
      )}
    >
      <div className="flex min-w-0 items-center gap-3">
        <Tooltip>
          <TooltipTrigger
            render={
              <button
                type="button"
                onClick={onTogglePreview}
                disabled={previewDisabled}
                aria-label={previewLabel}
                className={cn(
                  "relative grid size-10 shrink-0 place-items-center overflow-hidden rounded-[4px] bg-white/[0.06] text-muted-foreground shadow-sm outline-none ring-1 transition focus-visible:ring-2 focus-visible:ring-ring",
                  isActive ? "ring-primary/55" : "ring-white/[0.06]",
                  previewDisabled
                    ? "cursor-not-allowed opacity-55"
                    : "cursor-pointer",
                )}
              >
                {track.coverUrl ? (
                  <img
                    src={track.coverUrl}
                    alt={`${track.title} Cover`}
                    className="h-full w-full object-cover"
                    loading="lazy"
                  />
                ) : null}
                <span
                  className={cn(
                    "absolute inset-0 grid place-items-center bg-black/55 text-white transition-opacity",
                    isActivelyPlaying
                      ? "opacity-100"
                      : "opacity-0 group-hover:opacity-100 group-focus-within:opacity-100",
                  )}
                >
                  {isActivelyPlaying ? (
                    <Pause className="size-3.5 fill-current" />
                  ) : (
                    <Play className="ml-0.5 size-3.5 fill-current" />
                  )}
                </span>
              </button>
            }
          />
          <TooltipContent side="top" sideOffset={8}>
            {previewLabel}
          </TooltipContent>
        </Tooltip>
        <div className="min-w-0">
          <p
            className={cn(
              "truncate text-sm font-semibold leading-tight",
              isActive ? "text-primary" : "text-foreground",
            )}
          >
            {track.title}
          </p>
          <p className="mt-0.5 truncate text-xs text-muted-foreground">
            {track.artist}
          </p>
        </div>
      </div>

      <span className="justify-self-center text-sm font-semibold tabular-nums text-muted-foreground">
        {track.year}
      </span>

      <Tooltip>
        <TooltipTrigger
          render={
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              aria-label={`${track.title} hinzufügen`}
              disabled={disabled}
              onClick={onAdd}
              className="justify-self-end"
            >
              {isAdding ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Plus className="size-4" />
              )}
            </Button>
          }
        />
        <TooltipContent side="left" sideOffset={8}>
          {track.title} hinzufügen
        </TooltipContent>
      </Tooltip>
    </div>
  );
};
