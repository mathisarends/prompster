import { useRef } from "react";
import {
  MonitorSpeaker,
  Pause,
  Play,
  Shuffle,
  SkipBack,
  SkipForward,
  Volume2,
  VolumeX,
} from "lucide-react";

import { PlayerSlider } from "@/components/player-slider";
import { Button } from "@/components/ui/button";
import { type PlaylistTrack } from "@/lib/mockTracks";

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
  trackCount: number;
  volume: number;
  onPlayPause: () => void;
  onSelectTrackByOffset: (offset: number) => void;
  onSeek: (elapsedSeconds: number) => void;
  onVolumeChange: (volume: number) => void;
};

export const DeckPlayer = ({
  activeTrack,
  elapsedSeconds,
  durationSeconds,
  isPlaying,
  trackCount,
  volume,
  onPlayPause,
  onSelectTrackByOffset,
  onSeek,
  onVolumeChange,
}: DeckPlayerProps) => {
  const lastAudibleVolume = useRef(volume > 0 ? volume : 72);
  const isMuted = volume === 0;

  const toggleMute = () => {
    if (volume > 0) {
      lastAudibleVolume.current = volume;
      onVolumeChange(0);
      return;
    }

    onVolumeChange(lastAudibleVolume.current || 72);
  };

  const handleVolumeChange = (nextVolume: number) => {
    if (nextVolume > 0) {
      lastAudibleVolume.current = nextVolume;
    }

    onVolumeChange(nextVolume);
  };

  return (
    <div className="-mx-5 -mb-5 shrink-0 bg-white/[0.035] px-5 py-3">
      <div className="grid min-h-16 grid-cols-1 items-center gap-3 xl:grid-cols-[minmax(10rem,1fr)_minmax(18rem,1.25fr)_minmax(12rem,1fr)] xl:gap-5">
        <div className="flex min-w-0 items-center gap-3">
          <div className="h-12 w-12 shrink-0 overflow-hidden rounded-[3px] bg-white/[0.06]">
            {activeTrack ? (
              <img
                src={activeTrack.coverUrl}
                alt={`${activeTrack.title} Cover`}
                className="h-full w-full object-cover"
              />
            ) : null}
          </div>

          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold leading-tight text-foreground">
              {activeTrack?.title ?? "Kein Song ausgewählt"}
            </p>
            <p className="mt-0.5 truncate text-xs text-muted-foreground">
              {activeTrack?.artist ?? "Wähle einen Song aus der Liste"}
            </p>
          </div>
        </div>

        <div className="min-w-0">
          <div className="flex items-center justify-center gap-3">
            <Button
              type="button"
              size="icon-xs"
              variant="ghost"
              className="text-primary hover:bg-transparent hover:text-primary"
              aria-label="Zufallswiedergabe"
              disabled={!activeTrack}
            >
              <Shuffle className="size-4" />
            </Button>
            <Button
              type="button"
              size="icon-xs"
              variant="ghost"
              className="text-muted-foreground hover:bg-transparent hover:text-foreground"
              aria-label="Vorheriger Song"
              disabled={trackCount === 0}
              onClick={() => onSelectTrackByOffset(-1)}
            >
              <SkipBack className="size-4 fill-current" />
            </Button>
            <Button
              type="button"
              size="icon"
              className="size-9 rounded-full bg-foreground text-background shadow-none hover:scale-105 hover:bg-foreground"
              aria-label={isPlaying ? "Pause" : "Abspielen"}
              disabled={!activeTrack}
              onClick={onPlayPause}
            >
              {isPlaying ? (
                <Pause className="size-5 fill-current" />
              ) : (
                <Play className="ml-0.5 size-5 fill-current" />
              )}
            </Button>
            <Button
              type="button"
              size="icon-xs"
              variant="ghost"
              className="text-muted-foreground hover:bg-transparent hover:text-foreground"
              aria-label="Nächster Song"
              disabled={trackCount === 0}
              onClick={() => onSelectTrackByOffset(1)}
            >
              <SkipForward className="size-4 fill-current" />
            </Button>
          </div>

          <div className="mt-2 flex items-center gap-2">
            <span className="w-9 text-right text-[11px] tabular-nums text-muted-foreground">
              {formatDuration(elapsedSeconds)}
            </span>
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
            <span className="w-9 text-[11px] tabular-nums text-muted-foreground">
              {formatDuration(durationSeconds)}
            </span>
          </div>
        </div>

        <div className="flex min-w-0 items-center justify-end gap-3">
          <Button
            type="button"
            size="icon-xs"
            variant="ghost"
            className="text-muted-foreground hover:bg-transparent hover:text-foreground"
            aria-label="Gerät wechseln"
          >
            <MonitorSpeaker className="size-[1.125rem]" />
          </Button>
          <div className="flex w-32 items-center gap-2">
            <Button
              type="button"
              size="icon-xs"
              variant="ghost"
              className="text-muted-foreground hover:bg-transparent hover:text-foreground"
              aria-label={isMuted ? "Ton einschalten" : "Ton ausschalten"}
              onClick={toggleMute}
            >
              {isMuted ? (
                <VolumeX className="size-[1.125rem]" />
              ) : (
                <Volume2 className="size-[1.125rem]" />
              )}
            </Button>
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
