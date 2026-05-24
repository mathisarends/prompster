import { useEffect, useMemo, useState } from "react";

import { DeckPlayer } from "@/components/deck/deck-player";
import { DeckPlaylistTrackItem } from "@/components/deck/deck-playlist-track-item";
import { ScrollArea } from "@/components/ui/scroll-area";
import { SearchBar } from "@/components/deck/search-bar";
import { cn } from "@/lib/utils";
import type { PlaylistTrack } from "@/lib/playlist-track";
import { useOptimisticRemoval } from "@/hooks/useOptimisticRemoval";
import {
  usePlaybackState,
  type DeckPlaylistController,
} from "@/hooks/usePlaybackState";

export type { DeckPlaylistController } from "@/hooks/usePlaybackState";

type DeckPlaylistProps = {
  className?: string;
  initialTracks?: PlaylistTrack[];
  onVisibleTrackCountChange?: (count: number) => void;
  showHeader?: boolean;
  allowLocalRemoval?: boolean;
  onRemoveTrack?: (trackId: string) => Promise<void> | void;
  controller?: DeckPlaylistController;
};

export const DeckPlaylist = ({
  className,
  initialTracks = [],
  onVisibleTrackCountChange,
  showHeader = true,
  allowLocalRemoval = true,
  onRemoveTrack,
  controller,
}: DeckPlaylistProps) => {
  const [query, setQuery] = useState("");
  const playback = usePlaybackState(initialTracks, controller);
  const optimistic = useOptimisticRemoval(onRemoveTrack);

  const canRemoveTracks = allowLocalRemoval || Boolean(onRemoveTrack);

  const visibleTracks = useMemo(
    () => playback.tracks.filter((track) => !optimistic.hiddenIds.has(track.id)),
    [optimistic.hiddenIds, playback.tracks],
  );

  const activeTrack = useMemo(
    () => playback.tracks.find((track) => track.id === playback.activeTrackId) ?? null,
    [playback.activeTrackId, playback.tracks],
  );

  const filteredTracks = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return visibleTracks;
    return visibleTracks.filter((track) =>
      `${track.title} ${track.artist} ${track.year}`
        .toLowerCase()
        .includes(normalized),
    );
  }, [query, visibleTracks]);

  const removeTrack = (trackId: string) => {
    if (onRemoveTrack) {
      optimistic.removeTrack(trackId);
      return;
    }
    if (!allowLocalRemoval || controller) return;
    playback.removeTrackFromPlayback(trackId);
  };

  useEffect(() => {
    onVisibleTrackCountChange?.(filteredTracks.length);
  }, [filteredTracks.length, onVisibleTrackCountChange]);

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
            const isActive = track.id === playback.activeTrackId;
            const isPlayable = controller ? Boolean(track.spotifyUri) : true;

            return (
              <DeckPlaylistTrackItem
                key={track.id}
                track={track}
                trackNumber={index + 1}
                isActive={isActive}
                isPlaying={playback.isPlaying}
                isPlayable={isPlayable}
                canRemove={canRemoveTracks}
                isRemoving={optimistic.loadingIds.has(track.id)}
                onActivateTrack={() => {
                  if (isPlayable) playback.activateTrack(track.id);
                }}
                onTogglePlayPause={() => {
                  if (isActive) {
                    if (playback.isPlaying) {
                      playback.onPause();
                    } else {
                      playback.onResume();
                    }
                  } else if (isPlayable) {
                    playback.activateTrack(track.id);
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
        elapsedSeconds={playback.elapsedSeconds}
        durationSeconds={playback.durationSeconds}
        isPlaying={playback.isPlaying}
        volume={playback.volume}
        onPlayPause={playback.onPlayPause}
        onSeek={playback.onSeek}
        onVolumeChange={playback.onVolumeChange}
      />
    </div>
  );
};
