import { Pause, Play, Trash2 } from "lucide-react";

import { Button } from "@/shared/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/shared/ui/tooltip";
import { cn } from "@/shared/lib/utils";
import type { PlaylistTrack } from "@/features/spotify/lib/playlist-track";

const SoundBars = () => (
  <span aria-hidden className="flex h-4 w-4 items-end justify-center gap-[2px]">
    <span className="sound-bar h-[70%] w-[2px] rounded-full bg-current [--sound-bar-high:1] [--sound-bar-low:0.35] [animation-delay:-0.12s] [animation-duration:0.72s]" />
    <span className="sound-bar h-full w-[2px] rounded-full bg-current [--sound-bar-high:0.86] [--sound-bar-low:0.18] [animation-delay:-0.44s] [animation-duration:0.94s]" />
    <span className="sound-bar h-[58%] w-[2px] rounded-full bg-current [--sound-bar-high:1] [--sound-bar-low:0.28] [animation-delay:-0.28s] [animation-duration:0.82s]" />
    <span className="sound-bar h-[82%] w-[2px] rounded-full bg-current [--sound-bar-high:0.92] [--sound-bar-low:0.22] [animation-delay:-0.62s] [animation-duration:1.02s]" />
  </span>
);

type DeckPlaylistTrackItemProps = {
  track: PlaylistTrack;
  isActive: boolean;
  isPlaying: boolean;
  isPlayable: boolean;
  canRemove: boolean;
  isRemoving: boolean;
  onActivateTrack: () => void;
  onTogglePlayPause: () => void;
  onRemoveTrack: () => void;
};

export const DeckPlaylistTrackItem = ({
  track,
  isActive,
  isPlaying,
  isPlayable,
  canRemove,
  isRemoving,
  onActivateTrack,
  onTogglePlayPause,
  onRemoveTrack,
}: DeckPlaylistTrackItemProps) => {
  return (
    <div
      role="button"
      tabIndex={0}
      onDoubleClick={onActivateTrack}
      className={cn(
        "group relative grid grid-cols-[minmax(0,1fr)_64px_36px] items-center gap-x-3 rounded-md px-2 py-2.5 transition-colors",
        isActive ? "bg-white/[0.025]" : "hover:bg-white/[0.035]",
        !isPlayable ? "opacity-55" : null,
        isRemoving ? "pointer-events-none opacity-50" : null,
      )}
    >
      <div className="flex min-w-0 items-center gap-3">
        <div className="relative shrink-0">
          <div
            className={cn(
              "relative h-10 w-10 overflow-hidden rounded-[4px] bg-white/[0.06] shadow-sm ring-1 transition",
              isActive ? "ring-primary/55" : "ring-white/[0.06]",
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
            {isActive && isPlaying ? (
              <div className="absolute inset-x-0 bottom-0 flex h-4 items-center justify-center bg-gradient-to-t from-black/70 to-transparent text-primary">
                <SoundBars />
              </div>
            ) : null}
            <div className="absolute inset-0 grid place-items-center bg-black/55 opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
              <Tooltip>
                <TooltipTrigger
                  render={
                    <Button
                      size="icon-sm"
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

      <span className="justify-self-end text-sm font-semibold tabular-nums text-muted-foreground">
        {track.year}
      </span>

      <div className="flex items-center justify-end gap-0.5">
        {canRemove ? (
          <Tooltip>
            <TooltipTrigger
              render={
                <Button
                  size="icon-sm"
                  variant="ghost"
                  aria-label="Track löschen"
                  onClick={(event) => {
                    event.stopPropagation();
                    onRemoveTrack();
                  }}
                  disabled={isRemoving}
                  className="text-muted-foreground opacity-0 transition-opacity hover:bg-destructive/10 hover:text-destructive focus-visible:opacity-100 group-hover:opacity-100"
                >
                  <Trash2 className="size-4" />
                </Button>
              }
            />
            <TooltipContent side="top" sideOffset={8}>
              {isRemoving ? "Wird gelöscht..." : "Track löschen"}
            </TooltipContent>
          </Tooltip>
        ) : null}
      </div>
    </div>
  );
};
