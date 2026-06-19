import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowDownAZ, Check } from "lucide-react";

import type { SpotifyTrackResponse } from "@/api/generated/model";
import { DeckPlayer } from "@/features/deck/components/deck-player";
import { DeckPlaylistTrackItem } from "@/features/deck/components/deck-playlist-track-item";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/shared/ui/tooltip";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/shared/ui/dropdown-menu";
import { ScrollArea } from "@/shared/ui/scroll-area";
import { Skeleton } from "@/shared/ui/skeleton";
import { SearchBar } from "@/features/deck/components/search-bar";
import { SpotifyTrackSearchResults } from "@/features/deck/components/spotify-track-search-panel";
import { useLocalStorage } from "@/shared/hooks/useLocalStorage";
import { cn } from "@/shared/lib/utils";
import type { PlaylistTrack } from "@/features/spotify/lib/playlist-track";
import { useOptimisticRemoval } from "@/shared/hooks/useOptimisticRemoval";
import {
  usePlaybackState,
  type DeckPlaylistController,
} from "@/features/deck/hooks/usePlaybackState";

export type { DeckPlaylistController } from "@/features/deck/hooks/usePlaybackState";

type DeckPlaylistProps = {
  className?: string;
  initialTracks?: PlaylistTrack[];
  onVisibleTrackCountChange?: (count: number) => void;
  showHeader?: boolean;
  allowLocalRemoval?: boolean;
  onRemoveTrack?: (trackId: string) => Promise<void> | void;
  onAddSpotifyTrack?: (track: SpotifyTrackResponse) => Promise<void> | void;
  onPreviewSpotifyTrack?: (track: SpotifyTrackResponse) => void;
  previewTrack?: PlaylistTrack | null;
  isAddingSpotifyTrack?: boolean;
  addingSpotifyTrackId?: string | null;
  controller?: DeckPlaylistController;
  playlistUpdate?: {
    revision: number;
    event?: "set" | "track_added" | "track_removed" | "track_replaced";
  };
};

type SortMode = "playlist" | "title" | "artist" | "year-desc" | "year-asc";
type TrackAnimationState = "normal" | "entering" | "exiting" | "updated";

type AnimatedPlaylistTrack = {
  track: PlaylistTrack;
  state: TrackAnimationState;
  signature: string;
};

const TRACK_ENTER_MS = 520;
const TRACK_EXIT_MS = 280;
const PLAYLIST_SET_SKELETON_MS = 620;

const SORT_OPTIONS: { value: SortMode; label: string }[] = [
  { value: "playlist", label: "Playlist-Reihenfolge" },
  { value: "title", label: "Titel A-Z" },
  { value: "artist", label: "Artist A-Z" },
  { value: "year-desc", label: "Jahr neueste zuerst" },
  { value: "year-asc", label: "Jahr älteste zuerst" },
];

const compareText = (left: string, right: string) =>
  left.localeCompare(right, "de", { sensitivity: "base", numeric: true });

const parseYear = (year: string) => {
  const parsed = Number.parseInt(year, 10);
  return Number.isFinite(parsed) ? parsed : null;
};

const compareYear = (
  left: PlaylistTrack,
  right: PlaylistTrack,
  direction: "asc" | "desc",
) => {
  const leftYear = parseYear(left.year);
  const rightYear = parseYear(right.year);

  if (leftYear === null && rightYear === null) return 0;
  if (leftYear === null) return 1;
  if (rightYear === null) return -1;

  return direction === "asc" ? leftYear - rightYear : rightYear - leftYear;
};

const toSpotifyWebUrl = (spotifyUri: string): string | null => {
  const match = /^spotify:(track|album|artist|playlist):([A-Za-z0-9]+)$/.exec(
    spotifyUri,
  );
  if (!match) return null;

  const [, type, id] = match;
  return `https://open.spotify.com/${type}/${id}`;
};

const getTrackSignature = (track: PlaylistTrack) =>
  [
    track.title,
    track.artist,
    track.year,
    track.coverUrl,
    track.spotifyUri ?? "",
  ].join("\u001f");

const useAnimatedPlaylistTracks = (
  tracks: PlaylistTrack[],
): AnimatedPlaylistTrack[] => {
  const [renderedTracks, setRenderedTracks] = useState<AnimatedPlaylistTrack[]>(
    () =>
      tracks.map((track) => ({
        track,
        state: "normal",
        signature: getTrackSignature(track),
      })),
  );

  useEffect(() => {
    const nextById = new Map(tracks.map((track) => [track.id, track]));

    setRenderedTracks((currentTracks) => {
      const currentById = new Map(
        currentTracks.map((item) => [item.track.id, item]),
      );
      const nextItems = tracks.map<AnimatedPlaylistTrack>((track) => {
        const current = currentById.get(track.id);
        const signature = getTrackSignature(track);

        if (!current || current.state === "exiting") {
          return { track, state: "entering", signature };
        }

        return {
          track,
          signature,
          state: current.signature === signature ? "normal" : "updated",
        };
      });

      currentTracks.forEach((item, index) => {
        if (nextById.has(item.track.id) || item.state === "exiting") return;
        nextItems.splice(Math.min(index, nextItems.length), 0, {
          ...item,
          state: "exiting",
        });
      });

      return nextItems;
    });

    const settleTimer = window.setTimeout(() => {
      setRenderedTracks((currentTracks) =>
        currentTracks.map((item) =>
          item.state === "entering" || item.state === "updated"
            ? { ...item, state: "normal" }
            : item,
        ),
      );
    }, TRACK_ENTER_MS);

    const removeTimer = window.setTimeout(() => {
      setRenderedTracks((currentTracks) =>
        currentTracks.filter((item) => item.state !== "exiting"),
      );
    }, TRACK_EXIT_MS);

    return () => {
      window.clearTimeout(settleTimer);
      window.clearTimeout(removeTimer);
    };
  }, [tracks]);

  return renderedTracks;
};

const DeckPlaylistSkeletonTracks = () => (
  <div className="space-y-1 pb-3 pt-2">
    {Array.from({ length: 6 }).map((_, index) => (
      <div
        key={index}
        className="grid grid-cols-[minmax(0,1fr)_64px_36px] items-center gap-x-3 rounded-md px-2 py-2.5"
      >
        <div className="flex min-w-0 items-center gap-3">
          <Skeleton className="h-10 w-10 shrink-0 rounded-[4px] bg-white/[0.08]" />
          <div className="min-w-0 flex-1">
            <Skeleton className="h-3.5 w-[72%] bg-white/[0.1]" />
            <Skeleton className="mt-2 h-3 w-[46%] bg-white/[0.07]" />
          </div>
        </div>
        <Skeleton className="h-3.5 w-9 justify-self-end bg-white/[0.08]" />
        <Skeleton className="size-8 justify-self-end bg-white/[0.06]" />
      </div>
    ))}
  </div>
);

export const DeckPlaylist = ({
  className,
  initialTracks = [],
  onVisibleTrackCountChange,
  showHeader = true,
  allowLocalRemoval = true,
  onRemoveTrack,
  onAddSpotifyTrack,
  onPreviewSpotifyTrack,
  previewTrack = null,
  isAddingSpotifyTrack = false,
  addingSpotifyTrackId = null,
  controller,
  playlistUpdate,
}: DeckPlaylistProps) => {
  const [query, setQuery] = useState("");
  const [sortMode, setSortMode] = useLocalStorage<SortMode>(
    "deck-playlist-sort-mode",
    "playlist",
  );
  const searchInputRef = useRef<HTMLInputElement>(null);
  const playback = usePlaybackState(initialTracks, controller);
  const optimistic = useOptimisticRemoval(onRemoveTrack);
  const [showPlaylistSetSkeleton, setShowPlaylistSetSkeleton] = useState(false);

  const canRemoveTracks = allowLocalRemoval || Boolean(onRemoveTrack);
  const canAddSpotifyTrack = Boolean(onAddSpotifyTrack);
  const hasPlaybackController = Boolean(controller);

  const openTrackOnSpotify = (track: PlaylistTrack) => {
    if (!track.spotifyUri) return;

    const spotifyUrl =
      toSpotifyWebUrl(track.spotifyUri) ??
      `https://open.spotify.com/search/${encodeURIComponent(`${track.title} ${track.artist}`)}`;

    window.open(spotifyUrl, "_blank", "noopener,noreferrer");
  };

  const visibleTracks = useMemo(
    () =>
      playback.tracks.filter((track) => !optimistic.hiddenIds.has(track.id)),
    [optimistic.hiddenIds, playback.tracks],
  );

  const sortedTracks = useMemo(() => {
    if (sortMode === "playlist") return visibleTracks;

    return visibleTracks
      .map((track, index) => ({ index, track }))
      .sort((left, right) => {
        const result = (() => {
          switch (sortMode) {
            case "title":
              return compareText(left.track.title, right.track.title);
            case "artist":
              return compareText(left.track.artist, right.track.artist);
            case "year-desc":
              return compareYear(left.track, right.track, "desc");
            case "year-asc":
              return compareYear(left.track, right.track, "asc");
          }
        })();

        return result || left.index - right.index;
      })
      .map(({ track }) => track);
  }, [sortMode, visibleTracks]);

  const activeTrack = useMemo(() => {
    if (previewTrack && previewTrack.id === playback.activeTrackId) {
      return previewTrack;
    }
    return (
      playback.tracks.find((track) => track.id === playback.activeTrackId) ??
      null
    );
  }, [playback.activeTrackId, playback.tracks, previewTrack]);

  const filteredTracks = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return sortedTracks;
    return sortedTracks.filter((track) =>
      `${track.title} ${track.artist} ${track.year}`
        .toLowerCase()
        .includes(normalized),
    );
  }, [query, sortedTracks]);
  const animatedFilteredTracks = useAnimatedPlaylistTracks(filteredTracks);

  const activeSortOption =
    SORT_OPTIONS.find((option) => option.value === sortMode) ?? SORT_OPTIONS[0];
  const trimmedQuery = query.trim();
  const isSearchActive = trimmedQuery.length > 0;

  useEffect(() => {
    if (
      playlistUpdate?.event !== "set" ||
      !playlistUpdate.revision ||
      playlistUpdate.revision <= 0
    ) {
      return;
    }

    setShowPlaylistSetSkeleton(true);
    const timer = window.setTimeout(() => {
      setShowPlaylistSetSkeleton(false);
    }, PLAYLIST_SET_SKELETON_MS);

    return () => window.clearTimeout(timer);
  }, [playlistUpdate?.event, playlistUpdate?.revision]);

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

  const renderPlaylistTracks = (tracks: AnimatedPlaylistTrack[]) =>
    tracks.map(({ track, state }) => {
      const isActive = track.id === playback.activeTrackId;
      const isPlayable = Boolean(track.spotifyUri);

      return (
        <div
          key={track.id}
          className={cn(
            "deck-playlist-track-motion",
            state === "entering" ? "is-entering" : null,
            state === "exiting" ? "is-exiting" : null,
            state === "updated" ? "is-updated" : null,
          )}
        >
          <DeckPlaylistTrackItem
            track={track}
            isActive={isActive}
            isPlaying={playback.isPlaying}
            isPlayable={isPlayable}
            canRemove={canRemoveTracks}
            isRemoving={optimistic.loadingIds.has(track.id)}
            onActivateTrack={() => {
              if (isPlayable) playback.activateTrack(track.id);
            }}
            onTogglePlayPause={() => {
              if (!isPlayable) return;

              if (!hasPlaybackController) {
                openTrackOnSpotify(track);
                return;
              }

              if (isActive) {
                if (playback.isPlaying) {
                  playback.onPause();
                } else {
                  playback.onResume();
                }
              } else {
                playback.activateTrack(track.id);
              }
            }}
            onRemoveTrack={() => removeTrack(track.id)}
          />
        </div>
      );
    });

  return (
    <TooltipProvider delay={550}>
      <div className={cn("flex h-full min-h-0 flex-1 flex-col", className)}>
        <div className="shrink-0 pt-0.5 px-0.5">
          {showHeader ? (
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold tracking-tight">
                  Playlist
                </h3>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {filteredTracks.length} / 50 Songs
                </p>
              </div>
            </div>
          ) : null}

          <div className="mb-4 flex items-center gap-2">
            <div className="min-w-0 flex-1">
              <SearchBar
                value={query}
                inputRef={searchInputRef}
                onChange={(event) => {
                  setQuery(event.target.value);
                }}
                onClear={() => {
                  setQuery("");
                  searchInputRef.current?.focus();
                }}
                placeholder={
                  canAddSpotifyTrack
                    ? "Playlist und Spotify durchsuchen..."
                    : "Playlist durchsuchen: Titel, Artist, Jahr, Genre..."
                }
                containerClassName="px-0"
                inputClassName={cn(
                  "focus-visible:border-white/40 focus-visible:ring-white/30",
                  isSearchActive
                    ? "border-white/25 bg-background/90 text-foreground shadow-[0_0_0_1px_rgba(255,255,255,0.16)] focus-visible:border-white/40"
                    : "",
                )}
                iconClassName={isSearchActive ? "text-foreground/85" : ""}
              />
            </div>
            <DropdownMenu>
              <Tooltip>
                <TooltipTrigger
                  render={
                    <DropdownMenuTrigger
                      aria-label={`Playlist sortieren: ${activeSortOption.label}`}
                      className="inline-flex size-9 shrink-0 items-center justify-center rounded-md border border-border bg-background text-muted-foreground shadow-xs outline-none transition-colors hover:bg-muted hover:text-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 data-[state=open]:bg-muted data-[state=open]:text-foreground dark:border-input dark:bg-input/30 dark:hover:bg-input/50"
                    >
                      <ArrowDownAZ className="size-4" />
                    </DropdownMenuTrigger>
                  }
                />
                <TooltipContent side="bottom" sideOffset={8}>
                  Playlist sortieren
                </TooltipContent>
              </Tooltip>
              <DropdownMenuContent align="end" side="bottom" sideOffset={6}>
                {SORT_OPTIONS.map((option) => (
                  <DropdownMenuItem
                    key={option.value}
                    onClick={() => setSortMode(option.value)}
                  >
                    <span className="min-w-0 flex-1">{option.label}</span>
                    {option.value === sortMode ? (
                      <Check className="size-4 text-primary" />
                    ) : null}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-hidden">
          <ScrollArea className="h-full min-h-0 overflow-hidden pr-3">
            {showPlaylistSetSkeleton ? (
              <DeckPlaylistSkeletonTracks />
            ) : isSearchActive ? (
              <div className="space-y-5 pb-3 pt-2">
                {animatedFilteredTracks.length > 0 ? (
                  <section>
                    <div className="mb-2 px-1">
                      <h4 className="text-xs font-semibold uppercase text-muted-foreground">
                        In dieser Playlist
                      </h4>
                    </div>
                    <div className="space-y-1">
                      {renderPlaylistTracks(animatedFilteredTracks)}
                    </div>
                  </section>
                ) : null}

                {canAddSpotifyTrack && onAddSpotifyTrack ? (
                  <section>
                    <div className="mb-2 flex items-center justify-between gap-3 px-1">
                      <h4 className="text-xs font-semibold uppercase text-muted-foreground">
                        {filteredTracks.length > 0
                          ? "Weitere Songs"
                          : `Ergebnisse für "${trimmedQuery}"`}
                      </h4>
                    </div>
                    <SpotifyTrackSearchResults
                      query={query}
                      isAdding={isAddingSpotifyTrack}
                      addingTrackId={addingSpotifyTrackId}
                      activeTrackId={playback.activeTrackId}
                      isPlaying={playback.isPlaying}
                      onAddTrack={onAddSpotifyTrack}
                      onPreviewTrack={
                        hasPlaybackController
                          ? onPreviewSpotifyTrack
                          : undefined
                      }
                      onTogglePreviewPlayPause={
                        hasPlaybackController ? playback.onPlayPause : undefined
                      }
                    />
                  </section>
                ) : null}
              </div>
            ) : animatedFilteredTracks.length > 0 ? (
              <div className="space-y-1 pb-3 pt-2">
                {renderPlaylistTracks(animatedFilteredTracks)}
              </div>
            ) : (
              <div className="flex min-h-full flex-col items-center justify-center gap-3 px-3 py-8 text-center text-sm text-muted-foreground">
                <p>Keine Treffer in der Playlist.</p>
              </div>
            )}
          </ScrollArea>
        </div>

        {hasPlaybackController ? (
          <DeckPlayer
            className="-mx-5"
            activeTrack={activeTrack}
            elapsedSeconds={playback.elapsedSeconds}
            durationSeconds={playback.durationSeconds}
            isPlaying={playback.isPlaying}
            volume={playback.volume}
            shuffleEnabled={playback.shuffleEnabled}
            repeatMode={playback.repeatMode}
            hasAdjacentTracks={playback.hasAdjacentTracks}
            onPlayPause={playback.onPlayPause}
            onSeek={playback.onSeek}
            onVolumeChange={playback.onVolumeChange}
            onNextTrack={playback.onNextTrack}
            onPreviousTrack={playback.onPreviousTrack}
            onToggleShuffle={playback.onToggleShuffle}
            onCycleRepeat={playback.onCycleRepeat}
          />
        ) : null}
      </div>
    </TooltipProvider>
  );
};
