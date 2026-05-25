import { useCallback, useRef } from "react";
import {
  Pause,
  Play,
  Repeat,
  Repeat1,
  Shuffle,
  SkipBack,
  SkipForward,
  Volume2,
  VolumeX,
} from "lucide-react";

import { PlayerSlider } from "@/components/deck/player-slider";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useKeyboardShortcut } from "@/hooks/useKeyboardShortcut";
import { useWheel } from "@/hooks/useWheel";
import type { RepeatMode } from "@/hooks/usePlaybackState";
import { cn } from "@/lib/utils";
import { type PlaylistTrack } from "@/lib/playlist-track";

const DEFAULT_AUDIBLE_VOLUME = 72;
const VOLUME_WHEEL_STEP = 4;

const formatDuration = (seconds: number) => {
  const safeSeconds = Math.max(0, Math.round(seconds));
  const minutes = Math.floor(safeSeconds / 60);
  const remainingSeconds = safeSeconds % 60;

  return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
};

type DeckPlayerProps = {
  activeTrack: PlaylistTrack | null;
  elapsedSeconds: number;
  durationSeconds: number;
  isPlaying: boolean;
  volume: number;
  shuffleEnabled: boolean;
  repeatMode: RepeatMode;
  hasAdjacentTracks: boolean;
  onPlayPause: () => void;
  onSeek: (elapsedSeconds: number) => void;
  onVolumeChange: (volume: number) => void;
  onNextTrack: () => void;
  onPreviousTrack: () => void;
  onToggleShuffle: () => void;
  onCycleRepeat: () => void;
};

export const DeckPlayer = ({
  activeTrack,
  elapsedSeconds,
  durationSeconds,
  isPlaying,
  volume,
  shuffleEnabled,
  repeatMode,
  hasAdjacentTracks,
  onPlayPause,
  onSeek,
  onVolumeChange,
  onNextTrack,
  onPreviousTrack,
  onToggleShuffle,
  onCycleRepeat,
}: DeckPlayerProps) => {
  const lastAudibleVolume = useRef(
    volume > 0 ? volume : DEFAULT_AUDIBLE_VOLUME,
  );
  const hasActiveTrack = Boolean(activeTrack);
  const isMuted = volume === 0;
  const repeatActive = repeatMode !== "off";
  const RepeatIcon = repeatMode === "track" ? Repeat1 : Repeat;
  const repeatLabel =
    repeatMode === "off"
      ? "Wiederholung einschalten"
      : repeatMode === "playlist"
        ? "Einzelnen Track wiederholen"
        : "Wiederholung ausschalten";

  const handlePlayPause = useCallback(() => {
    if (!hasActiveTrack) {
      return;
    }

    onPlayPause();
  }, [hasActiveTrack, onPlayPause]);

  useKeyboardShortcut(
    {
      code: "Space",
      ctrlKey: false,
      metaKey: false,
      altKey: false,
      enabled: hasActiveTrack,
      ignoreInEditable: true,
    },
    handlePlayPause,
  );

  const toggleMute = () => {
    if (volume > 0) {
      lastAudibleVolume.current = volume;
      onVolumeChange(0);
      return;
    }

    onVolumeChange(lastAudibleVolume.current || DEFAULT_AUDIBLE_VOLUME);
  };

  const handleVolumeChange = useCallback(
    (nextVolume: number) => {
      const safeVolume = Math.min(100, Math.max(0, Math.round(nextVolume)));

      if (safeVolume > 0) {
        lastAudibleVolume.current = safeVolume;
      }

      onVolumeChange(safeVolume);
    },
    [onVolumeChange],
  );

  const handleVolumeWheel = useWheel({
    disabled: false,
    onChange: handleVolumeChange,
    step: VOLUME_WHEEL_STEP,
    value: volume,
  });

  const elapsedLabel = formatDuration(elapsedSeconds);
  const durationLabel = formatDuration(durationSeconds);

  return (
    <div className="deck-player group/player relative isolate -mx-5 -mb-5 mt-3 shrink-0 border-t border-white/[0.06] bg-background/85 px-5 pb-4 pt-3.5 backdrop-blur-xl transition-colors duration-200 hover:bg-background/90 focus-within:bg-background/90">
      <div className="deck-player-content grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-4">
        <div className="deck-player-meta flex min-w-0 items-center gap-3">
          <div className="deck-player-cover relative h-11 w-11 shrink-0 overflow-hidden rounded-lg bg-white/[0.06] shadow-[0_8px_22px_hsl(0_0%_0%/0.32)] ring-1 ring-white/[0.08]">
            {activeTrack?.coverUrl ? (
              <img
                src={activeTrack.coverUrl}
                alt={`${activeTrack.title} Cover`}
                className="h-full w-full object-cover"
              />
            ) : null}
          </div>

          <div className="min-w-0">
            <p className="truncate text-sm font-semibold leading-tight text-foreground">
              {activeTrack?.title ?? "Kein Song ausgewählt"}
            </p>
            <p className="deck-player-artist mt-0.5 truncate text-xs text-muted-foreground">
              {activeTrack?.artist ?? "Wähle einen Song aus der Liste"}
            </p>
          </div>
        </div>

        <div className="deck-player-transport flex items-center gap-1">
          <Tooltip>
            <TooltipTrigger
              render={
                <Button
                  type="button"
                  size="icon-sm"
                  variant="ghost"
                  className={cn(
                    "rounded-full text-muted-foreground hover:bg-white/[0.06] hover:text-foreground",
                    shuffleEnabled ? "text-primary hover:text-primary" : null,
                  )}
                  aria-label={
                    shuffleEnabled
                      ? "Shuffle ausschalten"
                      : "Shuffle einschalten"
                  }
                  aria-pressed={shuffleEnabled}
                  onClick={onToggleShuffle}
                >
                  <Shuffle className="size-4" />
                </Button>
              }
            />
            <TooltipContent side="top" sideOffset={8} showArrow={false}>
              {shuffleEnabled
                ? "Zufallswiedergabe ausschalten"
                : "Zufallswiedergabe einschalten"}
            </TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger
              render={
                <Button
                  type="button"
                  size="icon-sm"
                  variant="ghost"
                  className="rounded-full text-foreground/85 hover:bg-white/[0.06] hover:text-foreground disabled:opacity-40"
                  aria-label="Vorheriger Track"
                  disabled={!hasAdjacentTracks}
                  onClick={onPreviousTrack}
                >
                  <SkipBack className="size-[1.125rem] fill-current" />
                </Button>
              }
            />
            <TooltipContent side="top" sideOffset={8} showArrow={false}>
              Vorheriger Track
            </TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger
              render={
                <button
                  type="button"
                  className="deck-player-play grid size-10 shrink-0 place-items-center rounded-full bg-white text-slate-950 shadow-[0_10px_24px_hsl(0_0%_0%/0.42)] transition hover:scale-[1.04] hover:bg-white/95 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-default disabled:bg-white/[0.06] disabled:text-muted-foreground disabled:shadow-none disabled:hover:scale-100"
                  aria-label={
                    isPlaying ? "Track pausieren" : "Track fortsetzen"
                  }
                  disabled={!activeTrack}
                  onClick={handlePlayPause}
                >
                  {isPlaying ? (
                    <Pause className="size-[1.125rem] fill-current" />
                  ) : (
                    <Play className="ml-0.5 size-[1.125rem] fill-current" />
                  )}
                </button>
              }
            />
            <TooltipContent side="top" sideOffset={8} showArrow={false}>
              {isPlaying ? "Pause (Leertaste)" : "Abspielen (Leertaste)"}
            </TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger
              render={
                <Button
                  type="button"
                  size="icon-sm"
                  variant="ghost"
                  className="rounded-full text-foreground/85 hover:bg-white/[0.06] hover:text-foreground disabled:opacity-40"
                  aria-label="Nächster Track"
                  disabled={!hasAdjacentTracks}
                  onClick={onNextTrack}
                >
                  <SkipForward className="size-[1.125rem] fill-current" />
                </Button>
              }
            />
            <TooltipContent side="top" sideOffset={8} showArrow={false}>
              Nächster Track
            </TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger
              render={
                <Button
                  type="button"
                  size="icon-sm"
                  variant="ghost"
                  className={cn(
                    "rounded-full text-muted-foreground hover:bg-white/[0.06] hover:text-foreground",
                    repeatActive ? "text-primary hover:text-primary" : null,
                  )}
                  aria-label={repeatLabel}
                  aria-pressed={repeatActive}
                  onClick={onCycleRepeat}
                >
                  <RepeatIcon className="size-4" />
                </Button>
              }
            />
            <TooltipContent side="top" sideOffset={8} showArrow={false}>
              {repeatMode === "off"
                ? "Playlist wiederholen"
                : repeatMode === "playlist"
                  ? "Aktuellen Track wiederholen"
                  : "Wiederholung ausschalten"}
            </TooltipContent>
          </Tooltip>
        </div>

        <div className="deck-player-volume-slot flex items-center justify-end">
          <div
            className="deck-player-volume group relative flex shrink-0 items-center"
            onWheel={handleVolumeWheel}
          >
            <Button
              type="button"
              size="icon-sm"
              variant="ghost"
              className={cn(
                "rounded-full text-muted-foreground hover:bg-white/[0.06] hover:text-foreground",
                !isMuted ? "text-foreground" : null,
              )}
              aria-label={isMuted ? "Ton einschalten" : "Ton ausschalten"}
              aria-valuenow={volume}
              onClick={toggleMute}
            >
              {isMuted ? (
                <VolumeX className="size-[1.125rem]" />
              ) : (
                <Volume2 className="size-[1.125rem]" />
              )}
            </Button>

            <div className="deck-player-volume-popover pointer-events-none absolute right-[calc(100%+0.25rem)] top-1/2 flex w-28 -translate-y-1/2 items-center rounded-full border border-white/[0.08] bg-popover/95 px-3 py-2 opacity-0 shadow-[0_10px_28px_hsl(0_0%_0%/0.42)] backdrop-blur transition-opacity duration-150 group-hover:pointer-events-auto group-hover:opacity-100 group-focus-within:pointer-events-auto group-focus-within:opacity-100">
              <PlayerSlider
                min={0}
                max={100}
                value={volume}
                showTooltip={false}
                aria-label="Lautstärke"
                onChange={(event) =>
                  handleVolumeChange(Number(event.currentTarget.value))
                }
              />
            </div>
          </div>
        </div>
      </div>

      <div className="deck-player-progress mt-3 flex items-center gap-2.5">
        <span className="deck-player-time w-9 shrink-0 text-right text-[11px] font-medium tabular-nums text-muted-foreground">
          {elapsedLabel}
        </span>
        <div className="min-w-0 flex-1">
          <PlayerSlider
            min={0}
            max={durationSeconds}
            value={elapsedSeconds}
            showTooltip
            formatTooltip={(nextValue) => formatDuration(nextValue)}
            disabled={!activeTrack}
            aria-label="Trackposition"
            onChange={(event) => onSeek(Number(event.currentTarget.value))}
          />
        </div>
        <span className="deck-player-time w-9 shrink-0 text-[11px] font-medium tabular-nums text-muted-foreground">
          {durationLabel}
        </span>
      </div>
    </div>
  );
};
