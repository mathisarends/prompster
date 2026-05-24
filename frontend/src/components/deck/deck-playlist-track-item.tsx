import { Lock, LockOpen, MoreHorizontal, Pause, Play, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import type { PlaylistTrack } from "@/lib/playlist-track";

const SoundBars = () => (
  <span aria-hidden className="flex h-5 w-5 items-end justify-center gap-[2px]">
    <span className="sound-bar h-[70%] w-[2px] rounded-full bg-primary [--sound-bar-high:1] [--sound-bar-low:0.35] [animation-delay:-0.12s] [animation-duration:0.72s]" />
    <span className="sound-bar h-full w-[2px] rounded-full bg-primary [--sound-bar-high:0.86] [--sound-bar-low:0.18] [animation-delay:-0.44s] [animation-duration:0.94s]" />
    <span className="sound-bar h-[58%] w-[2px] rounded-full bg-primary [--sound-bar-high:1] [--sound-bar-low:0.28] [animation-delay:-0.28s] [animation-duration:0.82s]" />
    <span className="sound-bar h-[82%] w-[2px] rounded-full bg-primary [--sound-bar-high:0.92] [--sound-bar-low:0.22] [animation-delay:-0.62s] [animation-duration:1.02s]" />
  </span>
);

type DeckPlaylistTrackItemProps = {
  track: PlaylistTrack;
  isActive: boolean;
  isPlaying: boolean;
  isPlayable: boolean;
  canRemove: boolean;
  canToggleLock: boolean;
  isRemoving: boolean;
  isLocking: boolean;
  onActivateTrack: () => void;
  onTogglePlayPause: () => void;
  onRemoveTrack: () => void;
  onToggleLock: () => void;
};

export const DeckPlaylistTrackItem = ({
  track,
  isActive,
  isPlaying,
  isPlayable,
  canRemove,
  canToggleLock,
  isRemoving,
  isLocking,
  onActivateTrack,
  onTogglePlayPause,
  onRemoveTrack,
  onToggleLock,
}: DeckPlaylistTrackItemProps) => {
  const hasTrackActions = canRemove || canToggleLock;
  const lockLabel = track.isLocked ? "Track entsperren" : "Track sperren";

  return (
    <div
      role="button"
      tabIndex={0}
      onDoubleClick={onActivateTrack}
      className={cn(
        "group grid grid-cols-[minmax(0,1fr)_64px_36px] items-center gap-x-3 rounded-md px-2 py-3 transition-colors",
        isActive ? "bg-white/[0.07]" : "hover:bg-white/[0.04]",
        !isPlayable ? "opacity-55" : null,
        isRemoving ? "pointer-events-none opacity-50" : null,
      )}
    >
      <div className="flex min-w-0 items-center gap-3">
        <div className="relative h-10 w-10 shrink-0 overflow-hidden rounded-[4px] bg-white/[0.06] shadow-sm">
          {track.coverUrl ? (
            <img
              src={track.coverUrl}
              alt={`${track.title} Cover`}
              className="h-full w-full object-cover"
              loading="lazy"
            />
          ) : null}
          <div className="absolute inset-0 grid place-items-center bg-black/45 opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
            {isActive && isPlaying ? (
              <span className="opacity-100 group-hover:hidden">
                <SoundBars />
              </span>
            ) : null}
            <Tooltip>
              <TooltipTrigger
                render={
                  <Button
                    size="icon-xs"
                    variant="ghost"
                    className="text-white hover:bg-white/15 hover:text-white"
                    aria-label={
                      isActive && isPlaying
                        ? `${track.title} pausieren`
                        : `${track.title} abspielen`
                    }
                    onClick={(event) => {
                      event.stopPropagation();
                      onTogglePlayPause();
                    }}
                    disabled={!isPlayable || isRemoving}
                  >
                    {isActive && isPlaying ? (
                      <Pause className="size-3.5 fill-current" />
                    ) : (
                      <Play className="size-3.5 fill-current" />
                    )}
                  </Button>
                }
              />
              <TooltipContent side="top" sideOffset={8}>
                {!isPlayable
                  ? "Track ist ohne Spotify-URI nicht abspielbar"
                  : isActive && isPlaying
                    ? `${track.title} pausieren`
                    : `${track.title} abspielen`}
              </TooltipContent>
            </Tooltip>
          </div>
        </div>
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

      <div className="flex items-center justify-end">
        {hasTrackActions ? (
          <DropdownMenu>
            <Tooltip>
              <TooltipTrigger
                render={
                  <DropdownMenuTrigger
                    aria-label={`Mehr Optionen für ${track.title}`}
                    className="inline-flex size-8 items-center justify-center rounded-md text-muted-foreground opacity-0 outline-none transition-opacity hover:bg-white/[0.06] hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring group-hover:opacity-100 data-[state=open]:bg-white/[0.08] data-[state=open]:text-foreground data-[state=open]:opacity-100"
                  >
                    <MoreHorizontal className="size-4" />
                  </DropdownMenuTrigger>
                }
              />
              <TooltipContent side="left" sideOffset={8}>
                Mehr Optionen für {track.title}
              </TooltipContent>
            </Tooltip>
            <DropdownMenuContent align="end" side="bottom" sideOffset={6}>
              {canToggleLock ? (
                <DropdownMenuItem onClick={onToggleLock} disabled={isLocking}>
                  {track.isLocked ? <LockOpen /> : <Lock />}
                  <span>{isLocking ? "Wird aktualisiert..." : lockLabel}</span>
                </DropdownMenuItem>
              ) : null}
              {canRemove ? (
                <DropdownMenuItem
                  onClick={onRemoveTrack}
                  disabled={isRemoving}
                  className="text-destructive data-highlighted:bg-destructive/10 data-highlighted:text-destructive"
                >
                  <Trash2 />
                  <span>{isRemoving ? "Wird gelöscht..." : "Track löschen"}</span>
                </DropdownMenuItem>
              ) : null}
            </DropdownMenuContent>
          </DropdownMenu>
        ) : null}
      </div>
    </div>
  );
};
