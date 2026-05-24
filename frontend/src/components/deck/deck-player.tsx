import { useCallback, useRef } from "react";
import { Pause, Play, Volume2, VolumeX } from "lucide-react";

import { PlayerSlider } from "@/components/deck/player-slider";
import { Button } from "@/components/ui/button";
import { useKeyboardShortcut } from "@/hooks/useKeyboardShortcut";
import { useWheel } from "@/hooks/useWheel";
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
  onPlayPause: () => void;
  onSeek: (elapsedSeconds: number) => void;
  onVolumeChange: (volume: number) => void;
};

export const DeckPlayer = ({
  activeTrack,
  elapsedSeconds,
  durationSeconds,
  isPlaying,
  volume,
  onPlayPause,
  onSeek,
  onVolumeChange,
}: DeckPlayerProps) => {
  const lastAudibleVolume = useRef(
    volume > 0 ? volume : DEFAULT_AUDIBLE_VOLUME,
  );
  const hasActiveTrack = Boolean(activeTrack);
  const isMuted = volume === 0;

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
    <div className="deck-player group/player isolate -mx-5 -mb-5 mt-2 shrink-0 overflow-visible border-t border-white/[0.08] bg-background/78 px-5 pb-3 pt-4 shadow-[0_-18px_46px_hsl(222_52%_4%/0.36)] backdrop-blur-xl transition-[background-color,border-color,box-shadow] duration-200 hover:border-white/[0.12] hover:bg-background/86 focus-within:border-white/[0.12] focus-within:bg-background/86">
      <div className="deck-player-progress absolute inset-x-0 top-0">
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

      <div className="deck-player-content flex min-h-16 items-center gap-4 px-1.5">
        <button
          type="button"
          className="deck-player-cover group/cover relative h-12 w-12 shrink-0 overflow-hidden rounded-[4px] bg-white/[0.06] text-white shadow-[0_10px_28px_hsl(0_0%_0%/0.28)] ring-1 ring-white/[0.06] transition hover:ring-primary/55 focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-default disabled:opacity-60"
          aria-label={isPlaying ? "Track pausieren" : "Track fortsetzen"}
          disabled={!activeTrack}
          onClick={handlePlayPause}
        >
          {activeTrack?.coverUrl ? (
            <img
              src={activeTrack.coverUrl}
              alt={`${activeTrack.title} Cover`}
              className="h-full w-full object-cover"
            />
          ) : null}
          <span className="absolute inset-0 grid place-items-center bg-black/55 opacity-0 transition-opacity group-hover/cover:opacity-100 group-focus-visible/cover:opacity-100">
            {isPlaying ? (
              <Pause className="size-5 fill-current" />
            ) : (
              <Play className="ml-0.5 size-5 fill-current" />
            )}
          </span>
        </button>

        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold leading-tight text-foreground">
            {activeTrack?.title ?? "Kein Song ausgewählt"}
          </p>
          <p className="deck-player-artist mt-0.5 truncate text-xs text-muted-foreground">
            {activeTrack?.artist ?? "Wähle einen Song aus der Liste"}
          </p>
          <div className="deck-player-time mt-1 flex items-center gap-1.5 text-[11px] font-medium tabular-nums text-muted-foreground">
            <span>{elapsedLabel}</span>
            <span className="h-1 w-1 rounded-full bg-white/20" />
            <span>{durationLabel}</span>
          </div>
        </div>

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
  );
};
