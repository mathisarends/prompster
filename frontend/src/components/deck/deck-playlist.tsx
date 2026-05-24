import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { DeckPlayer } from "@/components/deck/deck-player";
import { DeckPlaylistTrackItem } from "@/components/deck/deck-playlist-track-item";
import { ScrollArea } from "@/components/ui/scroll-area";
import { SearchBar } from "@/components/deck/search-bar";
import { cn } from "@/lib/utils";
import { mockTracks, type PlaylistTrack } from "@/lib/mockTracks";

type DeckPlaylistProps = {
  className?: string;
  initialTracks?: PlaylistTrack[];
  onVisibleTrackCountChange?: (count: number) => void;
  showHeader?: boolean;
  allowLocalRemoval?: boolean;
  onRemoveTrack?: (trackId: string) => Promise<void> | void;
  controller?: DeckPlaylistController;
};

export type DeckPlaylistController = {
  isPlaying: boolean;
  activeTrackId: string | null;
  positionSeconds: number;
  durationSeconds: number;
  volume: number;
  onPlayTrack: (trackId: string) => void;
  onPause: () => void;
  onResume: () => void;
  onSeek: (seconds: number) => void;
  onVolumeChange: (volume: number) => void;
};

export const DeckPlaylist = ({
  className,
  initialTracks = mockTracks,
  onVisibleTrackCountChange,
  showHeader = true,
  allowLocalRemoval = true,
  onRemoveTrack,
  controller,
}: DeckPlaylistProps) => {
  const [localTracks, setLocalTracks] = useState(initialTracks);
  const [optimisticallyRemovedTrackIds, setOptimisticallyRemovedTrackIds] =
    useState<Set<string>>(() => new Set());
  const [removingTrackIds, setRemovingTrackIds] = useState<Set<string>>(
    () => new Set(),
  );
  const [query, setQuery] = useState("");
  const [localActiveTrackId, setLocalActiveTrackId] = useState<string | null>(
    initialTracks[0]?.id ?? null,
  );
  const [localIsPlaying, setLocalIsPlaying] = useState(
    initialTracks.length > 0,
  );
  const [localRemainingSeconds, setLocalRemainingSeconds] = useState(
    initialTracks[0]?.durationSeconds ?? 0,
  );
  const [localVolume, setLocalVolume] = useState(72);

  const activeTrackId = controller?.activeTrackId ?? localActiveTrackId;
  const isPlaying = controller?.isPlaying ?? localIsPlaying;
  const tracks = controller ? initialTracks : localTracks;
  const canRemoveTracks = allowLocalRemoval || Boolean(onRemoveTrack);

  const visibleTracks = useMemo(
    () =>
      tracks.filter((track) => !optimisticallyRemovedTrackIds.has(track.id)),
    [optimisticallyRemovedTrackIds, tracks],
  );

  const activeTrack = useMemo(
    () => tracks.find((track) => track.id === activeTrackId) ?? null,
    [activeTrackId, tracks],
  );

  const durationSeconds = activeTrack?.durationSeconds ?? 0;
  const elapsedSeconds = controller
    ? controller.positionSeconds
    : activeTrack
      ? Math.max(0, durationSeconds - localRemainingSeconds)
      : 0;

  const currentDurationSeconds = controller
    ? controller.durationSeconds
    : durationSeconds;

  const volume = controller?.volume ?? localVolume;

  const filteredTracks = useMemo(() => {
    const normalized = query.trim().toLowerCase();

    if (!normalized) {
      return visibleTracks;
    }

    return visibleTracks.filter((track) =>
      `${track.title} ${track.artist} ${track.year}`
        .toLowerCase()
        .includes(normalized),
    );
  }, [query, visibleTracks]);

  const removeTrack = (trackId: string) => {
    if (onRemoveTrack) {
      if (removingTrackIds.has(trackId)) {
        return;
      }

      setRemovingTrackIds((prev) => new Set(prev).add(trackId));
      setOptimisticallyRemovedTrackIds((prev) => new Set(prev).add(trackId));

      Promise.resolve(onRemoveTrack(trackId))
        .catch(() => {
          setOptimisticallyRemovedTrackIds((prev) => {
            const next = new Set(prev);
            next.delete(trackId);
            return next;
          });
          toast.error("Track konnte nicht aus der Playlist entfernt werden.");
        })
        .finally(() => {
          setRemovingTrackIds((prev) => {
            const next = new Set(prev);
            next.delete(trackId);
            return next;
          });
        });

      return;
    }

    if (controller || !allowLocalRemoval) return;
    setLocalTracks((prev) => prev.filter((track) => track.id !== trackId));
    if (trackId === activeTrackId) {
      setLocalActiveTrackId(null);
      setLocalIsPlaying(false);
      setLocalRemainingSeconds(0);
    }
  };

  const activateTrack = (trackId: string) => {
    if (controller) {
      controller.onPlayTrack(trackId);
      return;
    }

    const selectedTrack = tracks.find((track) => track.id === trackId);

    if (!selectedTrack) {
      return;
    }

    setLocalActiveTrackId(trackId);
    setLocalRemainingSeconds(selectedTrack.durationSeconds);
    setLocalIsPlaying(true);
  };

  useEffect(() => {
    onVisibleTrackCountChange?.(filteredTracks.length);
  }, [filteredTracks.length, onVisibleTrackCountChange]);

  useEffect(() => {
    if (controller || !activeTrack || !isPlaying) {
      return;
    }

    const intervalId = window.setInterval(() => {
      setLocalRemainingSeconds((seconds) => Math.max(seconds - 1, 0));
    }, 1000);

    return () => window.clearInterval(intervalId);
  }, [activeTrack, controller, isPlaying]);

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
            const isPlayable = controller ? Boolean(track.spotifyUri) : true;

            return (
              <DeckPlaylistTrackItem
                key={track.id}
                track={track}
                trackNumber={index + 1}
                isActive={isActive}
                isPlaying={isPlaying}
                isPlayable={isPlayable}
                canRemove={canRemoveTracks}
                isRemoving={removingTrackIds.has(track.id)}
                onActivateTrack={() => {
                  if (isPlayable) {
                    activateTrack(track.id);
                  }
                }}
                onTogglePlayPause={() => {
                  if (isActive && isPlaying) {
                    if (controller) {
                      controller.onPause();
                    } else {
                      setLocalIsPlaying(false);
                    }
                  } else if (isActive) {
                    if (controller) {
                      controller.onResume();
                    } else {
                      setLocalIsPlaying(true);
                    }
                  } else {
                    if (isPlayable) {
                      activateTrack(track.id);
                    }
                  }
                }}
                onRemoveTrack={() => removeTrack(track.id)}
              />
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
        durationSeconds={currentDurationSeconds}
        isPlaying={isPlaying}
        volume={volume}
        onPlayPause={() => {
          if (controller) {
            if (controller.isPlaying) {
              controller.onPause();
            } else {
              controller.onResume();
            }
            return;
          }
          setLocalIsPlaying((playing) => !playing);
        }}
        onSeek={(nextElapsedSeconds) => {
          if (controller) {
            controller.onSeek(nextElapsedSeconds);
            return;
          }
          setLocalRemainingSeconds(durationSeconds - nextElapsedSeconds);
        }}
        onVolumeChange={(nextVolume) => {
          if (controller) {
            controller.onVolumeChange(nextVolume);
            return;
          }
          setLocalVolume(nextVolume);
        }}
      />
    </div>
  );
};
