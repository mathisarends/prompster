import { useEffect, useMemo, useState } from "react";
import { Pause, Play, X } from "lucide-react";

import { DeckPlayer } from "@/components/deck-player";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { SearchBar } from "@/components/search-bar";
import { cn } from "@/lib/utils";
import { mockTracks, type PlaylistTrack } from "@/lib/mockTracks";

const SoundBars = () => (
  <span aria-hidden className="flex h-5 w-5 items-end justify-center gap-[2px]">
    <span className="sound-bar h-[70%] w-[2px] rounded-full bg-primary [--sound-bar-high:1] [--sound-bar-low:0.35] [animation-delay:-0.12s] [animation-duration:0.72s]" />
    <span className="sound-bar h-full w-[2px] rounded-full bg-primary [--sound-bar-high:0.86] [--sound-bar-low:0.18] [animation-delay:-0.44s] [animation-duration:0.94s]" />
    <span className="sound-bar h-[58%] w-[2px] rounded-full bg-primary [--sound-bar-high:1] [--sound-bar-low:0.28] [animation-delay:-0.28s] [animation-duration:0.82s]" />
    <span className="sound-bar h-[82%] w-[2px] rounded-full bg-primary [--sound-bar-high:0.92] [--sound-bar-low:0.22] [animation-delay:-0.62s] [animation-duration:1.02s]" />
  </span>
);

type DeckPlaylistProps = {
  className?: string;
  initialTracks?: PlaylistTrack[];
  onVisibleTrackCountChange?: (count: number) => void;
  showHeader?: boolean;
};

export const DeckPlaylist = ({
  className,
  initialTracks = mockTracks,
  onVisibleTrackCountChange,
  showHeader = true,
}: DeckPlaylistProps) => {
  const [tracks, setTracks] = useState(initialTracks);
  const [query, setQuery] = useState("");
  const [activeTrackId, setActiveTrackId] = useState<string | null>(
    initialTracks[0]?.id ?? null,
  );
  const [isPlaying, setIsPlaying] = useState(initialTracks.length > 0);
  const [remainingSeconds, setRemainingSeconds] = useState(
    initialTracks[0]?.durationSeconds ?? 0,
  );
  const [volume, setVolume] = useState(72);

  const activeTrack = useMemo(
    () => tracks.find((track) => track.id === activeTrackId) ?? null,
    [activeTrackId, tracks],
  );

  const activeTrackIndex = useMemo(
    () => tracks.findIndex((track) => track.id === activeTrackId),
    [activeTrackId, tracks],
  );

  const durationSeconds = activeTrack?.durationSeconds ?? 0;
  const elapsedSeconds = activeTrack
    ? Math.max(0, durationSeconds - remainingSeconds)
    : 0;

  const filteredTracks = useMemo(() => {
    const normalized = query.trim().toLowerCase();

    if (!normalized) {
      return tracks;
    }

    return tracks.filter((track) =>
      `${track.title} ${track.artist} ${track.year}`
        .toLowerCase()
        .includes(normalized),
    );
  }, [query, tracks]);

  const removeTrack = (trackId: string) => {
    setTracks((prev) => prev.filter((track) => track.id !== trackId));
    if (trackId === activeTrackId) {
      setActiveTrackId(null);
      setIsPlaying(false);
      setRemainingSeconds(0);
    }
  };

  const activateTrack = (trackId: string) => {
    const selectedTrack = tracks.find((track) => track.id === trackId);

    if (!selectedTrack) {
      return;
    }

    setActiveTrackId(trackId);
    setRemainingSeconds(selectedTrack.durationSeconds);
    setIsPlaying(true);
  };

  const selectTrackByOffset = (offset: number) => {
    if (tracks.length === 0) {
      return;
    }

    const currentIndex = activeTrackIndex >= 0 ? activeTrackIndex : 0;
    const nextIndex = (currentIndex + offset + tracks.length) % tracks.length;
    activateTrack(tracks[nextIndex].id);
  };

  useEffect(() => {
    onVisibleTrackCountChange?.(filteredTracks.length);
  }, [filteredTracks.length, onVisibleTrackCountChange]);

  useEffect(() => {
    if (!activeTrack || !isPlaying) {
      return;
    }

    const intervalId = window.setInterval(() => {
      setRemainingSeconds((seconds) => Math.max(seconds - 1, 0));
    }, 1000);

    return () => window.clearInterval(intervalId);
  }, [activeTrack, isPlaying]);

  return (
    <div className={cn("flex min-h-0 flex-1 flex-col", className)}>
      {showHeader ? (
        <div className="mb-3 flex items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold tracking-tight">Playlist</h3>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {filteredTracks.length} / 50 Songs
            </p>
          </div>
        </div>
      ) : null}

      <SearchBar
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Playlist durchsuchen: Titel, Artist, Jahr, Genre..."
        containerClassName="mb-4 px-0"
      />

      <div className="grid grid-cols-[40px_minmax(0,1fr)_72px_40px] gap-x-4 pr-3 items-center border-b border-white/[0.06] pb-3 text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
        <span className="justify-self-center">#</span>
        <span>Titel</span>
        <span className="justify-self-end">Jahr</span>
        <span />
      </div>

      <ScrollArea className="min-h-0 flex-1">
        <div className="space-y-1 pt-2 pb-3">
          {filteredTracks.map((track, index) => {
            const isActive = track.id === activeTrackId;

            return (
              <div
                key={track.id}
                role="button"
                tabIndex={0}
                onDoubleClick={() => activateTrack(track.id)}
                className={cn(
                  "group grid grid-cols-[40px_minmax(0,1fr)_72px_40px] gap-x-4 px-2 items-center rounded-md py-3 transition-colors",
                  isActive ? "bg-white/[0.07]" : "hover:bg-white/[0.04]",
                )}
              >
                <div className="relative grid h-7 place-items-center text-sm tabular-nums text-muted-foreground">
                  {isActive && isPlaying ? (
                    <span className="group-hover:hidden">
                      <SoundBars />
                    </span>
                  ) : (
                    <span className="group-hover:hidden">{index + 1}</span>
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
                    onClick={() => {
                      if (isActive && isPlaying) {
                        setIsPlaying(false);
                      } else if (isActive) {
                        setIsPlaying(true);
                      } else {
                        activateTrack(track.id);
                      }
                    }}
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
                    <img
                      src={track.coverUrl}
                      alt={`${track.title} Cover`}
                      className="h-full w-full object-cover"
                      loading="lazy"
                    />
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
                  <Button
                    size="icon-xs"
                    variant="ghost"
                    className="text-muted-foreground opacity-0 transition-opacity hover:text-foreground group-hover:opacity-100 focus-visible:opacity-100"
                    aria-label={`${track.title} entfernen`}
                    onClick={(event) => {
                      event.stopPropagation();
                      removeTrack(track.id);
                    }}
                  >
                    <X className="size-3.5" />
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
        {filteredTracks.length === 0 ? (
          <div className="px-3 py-8 text-center text-sm text-muted-foreground">
            Keine Treffer in der Playlist.
          </div>
        ) : null}
      </ScrollArea>

      <DeckPlayer
        activeTrack={activeTrack}
        elapsedSeconds={elapsedSeconds}
        durationSeconds={durationSeconds}
        isPlaying={isPlaying}
        trackCount={tracks.length}
        volume={volume}
        onPlayPause={() => setIsPlaying((playing) => !playing)}
        onSelectTrackByOffset={selectTrackByOffset}
        onSeek={(nextElapsedSeconds) => {
          setRemainingSeconds(durationSeconds - nextElapsedSeconds);
        }}
        onVolumeChange={setVolume}
      />
    </div>
  );
};
