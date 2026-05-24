import { Pause, Play, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { PlaylistTrack } from "@/lib/mockTracks";

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
  trackNumber: number;
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
  trackNumber,
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
        "group grid grid-cols-[40px_minmax(0,1fr)_72px_40px] items-center gap-x-4 rounded-md px-2 py-3 transition-colors",
        isActive ? "bg-white/[0.07]" : "hover:bg-white/[0.04]",
        !isPlayable ? "opacity-55" : null,
        isRemoving ? "pointer-events-none opacity-50" : null,
      )}
    >
      <div className="relative grid h-7 place-items-center text-sm tabular-nums text-muted-foreground">
        {isActive && isPlaying ? (
          <span className="group-hover:hidden">
            <SoundBars />
          </span>
        ) : (
          <span className="group-hover:hidden">{trackNumber}</span>
        )}
        <Button
          size="icon-xs"
          variant="ghost"
          className="absolute hidden text-foreground hover:bg-transparent group-hover:inline-flex"
          aria-label={
            isActive && isPlaying
              ? `${track.title} pausieren`
              : `${track.title} abspielen`
          }
          onClick={onTogglePlayPause}
          disabled={!isPlayable || isRemoving}
          title={
            !isPlayable
              ? "Track ist ohne Spotify-URI nicht abspielbar"
              : undefined
          }
        >
          {isActive && isPlaying ? (
            <Pause className="size-3.5 fill-current" />
          ) : (
            <Play className="size-3.5 fill-current" />
          )}
        </Button>
      </div>

      <div className="flex min-w-0 items-center gap-3">
        <div className="h-10 w-10 shrink-0 overflow-hidden rounded-[4px] bg-white/[0.06] shadow-sm">
          {track.coverUrl ? (
            <img
              src={track.coverUrl}
              alt={`${track.title} Cover`}
              className="h-full w-full object-cover"
              loading="lazy"
            />
          ) : null}
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

      <span className="justify-self-end text-xs font-medium tabular-nums text-muted-foreground">
        {track.year}
      </span>

      <div className="flex items-center justify-end">
        {canRemove ? (
          <Button
            size="icon-xs"
            variant="ghost"
            className="text-muted-foreground opacity-0 transition-opacity hover:text-foreground group-hover:opacity-100 focus-visible:opacity-100"
            aria-label={`${track.title} entfernen`}
            onClick={(event) => {
              event.stopPropagation();
              onRemoveTrack();
            }}
            disabled={isRemoving}
            title={isRemoving ? "Track wird entfernt..." : undefined}
          >
            <X className="size-3.5" />
          </Button>
        ) : null}
      </div>
    </div>
  );
};
