import { Loader2, Pause, Play, Undo2 } from "lucide-react";

import type { UserCurationEventResponse } from "@/api/generated/model";
import { Button } from "@/shared/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/shared/ui/tooltip";
import { cn } from "@/shared/lib/utils";

import {
  UserCurationFallbackIcon,
  userCurationEventMeta,
} from "../user-curation-event-meta";

type UserCurationEventChipProps = {
  event: UserCurationEventResponse;
  isRestoring?: boolean;
  isDisabled?: boolean;
  isPlaying: boolean;
  onRestore?: () => void;
  onTogglePlayback?: (event: UserCurationEventResponse) => void;
  className?: string;
};

const UserCurationEventCover = ({
  event,
  isPlaying,
  onTogglePlayback,
}: {
  event: UserCurationEventResponse;
  isPlaying: boolean;
  onTogglePlayback?: (event: UserCurationEventResponse) => void;
}) => {
  const canPlayTrack = Boolean(event.trackSpotifyUri && onTogglePlayback);
  const playbackLabel = isPlaying
    ? `${event.trackTitle} pausieren`
    : `${event.trackTitle} im Player abspielen`;
  const cover = event.trackCoverUrl ? (
    <img
      src={event.trackCoverUrl}
      alt={event.trackTitle}
      className="h-full w-full object-cover"
      loading="lazy"
    />
  ) : (
    <UserCurationFallbackIcon className="size-5" />
  );

  if (!canPlayTrack) {
    return (
      <div className="relative grid size-10 shrink-0 place-items-center overflow-hidden rounded-md bg-white/[0.06] text-muted-foreground ring-1 ring-white/[0.04]">
        {cover}
      </div>
    );
  }

  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <button
            type="button"
            aria-label={playbackLabel}
            onClick={() => onTogglePlayback?.(event)}
            className="group/cover relative grid size-10 shrink-0 place-items-center overflow-hidden rounded-md bg-white/[0.06] text-muted-foreground ring-1 ring-white/[0.04] transition hover:ring-primary/45 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {cover}
            <span className="absolute inset-0 grid place-items-center bg-black/55 text-white opacity-0 transition-opacity group-hover/cover:opacity-100 group-focus-visible/cover:opacity-100">
              {isPlaying ? (
                <Pause className="size-3.5 fill-current" />
              ) : (
                <Play className="size-3.5 fill-current" />
              )}
            </span>
          </button>
        }
      />
      <TooltipContent side="top" sideOffset={8}>
        {isPlaying ? "Pausieren" : "Im Player abspielen"}
      </TooltipContent>
    </Tooltip>
  );
};

export const UserCurationEventChip = ({
  event,
  isRestoring,
  isDisabled,
  isPlaying,
  onRestore,
  onTogglePlayback,
  className,
}: UserCurationEventChipProps) => {
  const meta = userCurationEventMeta[event.eventType];
  const Icon = meta.Icon;

  return (
    <div
      className={cn(
        "group/event flex min-w-0 flex-1 basis-64 items-center gap-2.5 rounded-xl border border-white/[0.06] bg-card/55 py-1.5 pl-1.5 pr-3 shadow-sm shadow-black/20 backdrop-blur-sm sm:max-w-[17rem]",
        className,
      )}
    >
      <UserCurationEventCover
        event={event}
        isPlaying={isPlaying}
        onTogglePlayback={onTogglePlayback}
      />

      <div className="min-w-0 flex-1">
        <div className="flex min-w-0 items-center gap-1.5">
          <span
            className={cn(
              "inline-flex h-5 shrink-0 items-center gap-1 rounded-md border px-1.5 text-[11px] font-semibold leading-none",
              meta.className,
            )}
          >
            <Icon className="size-3" />
            {meta.label}
          </span>
          <p className="min-w-0 truncate text-[13px] font-semibold leading-tight text-foreground">
            {event.trackTitle}
          </p>
        </div>
        <p className="mt-0.5 truncate text-[11px] text-muted-foreground">
          {event.trackArtist}
        </p>
      </div>

      {onRestore ? (
        <Tooltip>
          <TooltipTrigger
            render={
              <Button
                type="button"
                variant="ghost"
                size="icon-xs"
                disabled={isDisabled}
                aria-label={meta.restoreTooltip}
                onClick={onRestore}
                className="pointer-events-none shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover/event:pointer-events-auto group-hover/event:opacity-100 hover:bg-white/10 hover:text-foreground"
              >
                {isRestoring ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  <Undo2 className="size-3.5" />
                )}
              </Button>
            }
          />
          <TooltipContent side="top" sideOffset={6} showArrow={false}>
            {isRestoring ? "Wird rueckgaengig gemacht..." : meta.restoreTooltip}
          </TooltipContent>
        </Tooltip>
      ) : null}
    </div>
  );
};
