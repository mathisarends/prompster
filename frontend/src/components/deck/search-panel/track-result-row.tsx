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
  onAdd: () => void;
  onTogglePreview: () => void;
};

export const TrackResultRow = ({
  track,
  isAdding,
  disabled,
  isActive,
  isPlaying,
  onAdd,
  onTogglePreview,
}: TrackResultRowProps) => {
  const isActivelyPlaying = isActive && isPlaying;
  const previewLabel = isActivelyPlaying
    ? `${track.title} pausieren`
    : `${track.title} anspielen`;

  return (
    <div className="group grid grid-cols-[40px_minmax(0,1fr)_auto] items-center gap-3 rounded-md px-2 py-2 transition-colors hover:bg-white/[0.04]">
      <Tooltip>
        <TooltipTrigger
          render={
            <button
              type="button"
              onClick={onTogglePreview}
              aria-label={previewLabel}
              className={cn(
                "relative grid size-10 shrink-0 place-items-center overflow-hidden rounded-[4px] bg-white/[0.06] text-muted-foreground shadow-sm outline-none ring-1 ring-white/[0.04] transition focus-visible:ring-2 focus-visible:ring-ring",
                isActive ? "ring-primary/55" : "hover:ring-white/[0.12]",
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
            isActive ? "text-primary" : null,
          )}
        >
          {track.title}
        </p>
        <p className="mt-0.5 truncate text-xs text-muted-foreground">
          {track.artist}
          {track.album ? ` · ${track.album}` : ""}
          {track.year ? ` · ${track.year}` : ""}
        </p>
      </div>
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
