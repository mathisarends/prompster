import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowDownAZ, Check, Plus, X } from "lucide-react";

import type { SpotifyTrackResponse } from "@/api/generated/model";
import { Button } from "@/components/ui/button";
import { DeckPlayer } from "@/components/deck/deck-player";
import { DeckPlaylistTrackItem } from "@/components/deck/deck-playlist-track-item";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ScrollArea } from "@/components/ui/scroll-area";
import { SearchBar } from "@/components/deck/search-bar";
import { SpotifyTrackSearchPanel } from "@/components/deck/spotify-track-search-panel";
import { useLocalStorage } from "@/hooks/useLocalStorage";
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
  onToggleTrackPin?: (
    trackId: string,
    isPinned: boolean,
  ) => Promise<void> | void;
  onAddSpotifyTrack?: (track: SpotifyTrackResponse) => Promise<void> | void;
  onPreviewSpotifyTrack?: (track: SpotifyTrackResponse) => void;
  previewTrack?: PlaylistTrack | null;
  isAddingSpotifyTrack?: boolean;
  addingSpotifyTrackId?: string | null;
  pinningTrackId?: string | null;
  controller?: DeckPlaylistController;
};

type SortMode = "playlist" | "title" | "artist" | "year-desc" | "year-asc";

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

export const DeckPlaylist = ({
  className,
  initialTracks = [],
  onVisibleTrackCountChange,
  showHeader = true,
  allowLocalRemoval = true,
  onRemoveTrack,
  onToggleTrackPin,
  onAddSpotifyTrack,
  onPreviewSpotifyTrack,
  previewTrack = null,
  isAddingSpotifyTrack = false,
  addingSpotifyTrackId = null,
  pinningTrackId = null,
  controller,
}: DeckPlaylistProps) => {
  const [query, setQuery] = useState("");
  const [sortMode, setSortMode] = useLocalStorage<SortMode>(
    "deck-playlist-sort-mode",
    "playlist",
  );
  const [spotifySearchOpen, setSpotifySearchOpen] = useState(false);
  const [spotifySearchQuery, setSpotifySearchQuery] = useState("");
  const searchInputRef = useRef<HTMLInputElement>(null);
  const searchAreaRef = useRef<HTMLDivElement>(null);
  const spotifyPanelRef = useRef<HTMLDivElement>(null);
  const addTrackToggleRef = useRef<HTMLSpanElement>(null);
  const playback = usePlaybackState(initialTracks, controller);
  const optimistic = useOptimisticRemoval(onRemoveTrack);

  const canRemoveTracks = allowLocalRemoval || Boolean(onRemoveTrack);
  const canToggleTrackPin = Boolean(onToggleTrackPin);
  const canAddSpotifyTrack = Boolean(onAddSpotifyTrack);

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

  const activeSortOption =
    SORT_OPTIONS.find((option) => option.value === sortMode) ?? SORT_OPTIONS[0];

  const removeTrack = (trackId: string) => {
    if (onRemoveTrack) {
      optimistic.removeTrack(trackId);
      return;
    }
    if (!allowLocalRemoval || controller) return;
    playback.removeTrackFromPlayback(trackId);
  };

  const toggleTrackPin = (track: PlaylistTrack) => {
    void onToggleTrackPin?.(track.id, track.isPinned);
  };

  const isSpotifySearchActive = canAddSpotifyTrack && spotifySearchOpen;
  const searchValue = isSpotifySearchActive ? spotifySearchQuery : query;

  const openSpotifySearch = (initialQuery = "") => {
    const trimmed = initialQuery.trim();
    setSpotifySearchQuery((current) => current || trimmed);
    setSpotifySearchOpen(true);
  };

  const closeSpotifySearch = () => {
    setSpotifySearchOpen(false);
  };

  useEffect(() => {
    onVisibleTrackCountChange?.(filteredTracks.length);
  }, [filteredTracks.length, onVisibleTrackCountChange]);

  useEffect(() => {
    if (isSpotifySearchActive) {
      window.requestAnimationFrame(() => searchInputRef.current?.focus());
    }
  }, [isSpotifySearchActive]);

  useEffect(() => {
    if (!isSpotifySearchActive) return;

    const closeOnOutsidePointerDown = (event: PointerEvent) => {
      const target = event.target;
      if (!(target instanceof Node)) return;

      if (
        searchAreaRef.current?.contains(target) ||
        spotifyPanelRef.current?.contains(target) ||
        addTrackToggleRef.current?.contains(target)
      ) {
        return;
      }

      closeSpotifySearch();
    };

    document.addEventListener("pointerdown", closeOnOutsidePointerDown);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsidePointerDown);
    };
  }, [isSpotifySearchActive]);

  return (
    <TooltipProvider delay={550}>
      <div className={cn("flex h-full min-h-0 flex-1 flex-col", className)}>
        <div className="shrink-0">
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
            <div ref={searchAreaRef} className="min-w-0 flex-1">
              <SearchBar
                value={searchValue}
                inputRef={searchInputRef}
                onChange={(event) => {
                  if (isSpotifySearchActive) {
                    setSpotifySearchQuery(event.target.value);
                  } else {
                    setQuery(event.target.value);
                  }
                }}
                onClear={() => {
                  if (isSpotifySearchActive) {
                    setSpotifySearchQuery("");
                  } else {
                    setQuery("");
                  }
                  searchInputRef.current?.focus();
                }}
                placeholder={
                  isSpotifySearchActive
                    ? "Fang an zu tippen, um bei Spotify zu suchen..."
                    : "Playlist durchsuchen: Titel, Artist, Jahr, Genre..."
                }
                containerClassName="px-0"
                inputClassName={cn(
                  isSpotifySearchActive
                    ? "border-primary/45 bg-background/85 text-foreground shadow-[0_0_0_1px_hsl(141_73%_42%/0.18)] focus-visible:border-primary/70"
                    : "",
                )}
                iconClassName={isSpotifySearchActive ? "text-primary" : ""}
              />
            </div>
            {!isSpotifySearchActive ? (
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
            ) : null}
            {canAddSpotifyTrack ? (
              <Tooltip>
                <TooltipTrigger
                  render={
                    <span ref={addTrackToggleRef} className="inline-flex">
                      <Button
                        type="button"
                        variant="outline"
                        size="icon"
                        aria-label={
                          isSpotifySearchActive
                            ? "Spotify-Suche schließen"
                            : "Song über Spotify hinzufügen"
                        }
                        aria-expanded={spotifySearchOpen}
                        className={cn(
                          isSpotifySearchActive
                            ? "border-primary/50 bg-primary/10 text-primary hover:bg-primary/15 hover:text-primary"
                            : "",
                        )}
                        onClick={() => {
                          if (isSpotifySearchActive) {
                            closeSpotifySearch();
                          } else {
                            openSpotifySearch(query);
                          }
                        }}
                      >
                        {isSpotifySearchActive ? (
                          <X className="size-4" />
                        ) : (
                          <Plus className="size-4" />
                        )}
                      </Button>
                    </span>
                  }
                />
                <TooltipContent side="bottom" sideOffset={8}>
                  {isSpotifySearchActive
                    ? "Spotify-Suche schließen"
                    : "Song über Spotify hinzufügen"}
                </TooltipContent>
              </Tooltip>
            ) : null}
          </div>

          {onAddSpotifyTrack && spotifySearchOpen ? (
            <SpotifyTrackSearchPanel
              panelRef={spotifyPanelRef}
              query={spotifySearchQuery}
              isAdding={isAddingSpotifyTrack}
              addingTrackId={addingSpotifyTrackId}
              activeTrackId={playback.activeTrackId}
              isPlaying={playback.isPlaying}
              onAddTrack={onAddSpotifyTrack}
              onPreviewTrack={onPreviewSpotifyTrack}
              onTogglePreviewPlayPause={playback.onPlayPause}
            />
          ) : null}
        </div>

        <div className="min-h-0 flex-1 overflow-hidden">
          <ScrollArea className="h-full min-h-0 overflow-hidden pr-3">
            {filteredTracks.length > 0 ? (
              <div className="space-y-1 pb-3 pt-2">
                {filteredTracks.map((track) => {
                  const isActive = track.id === playback.activeTrackId;
                  const isPlayable = controller
                    ? Boolean(track.spotifyUri)
                    : true;

                  return (
                    <DeckPlaylistTrackItem
                      key={track.id}
                      track={track}
                      isActive={isActive}
                      isPlaying={playback.isPlaying}
                      isPlayable={isPlayable}
                      canRemove={canRemoveTracks}
                      canTogglePin={canToggleTrackPin}
                      isRemoving={optimistic.loadingIds.has(track.id)}
                      isPinning={pinningTrackId === track.id}
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
                      onTogglePin={() => toggleTrackPin(track)}
                    />
                  );
                })}
              </div>
            ) : (
              <div className="flex min-h-full flex-col items-center justify-center gap-3 px-3 py-8 text-center text-sm text-muted-foreground">
                <p>Keine Treffer in der Playlist.</p>
                {canAddSpotifyTrack && query.trim() ? (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => openSpotifySearch(query)}
                  >
                    <Plus className="size-4" />
                    Bei Spotify suchen
                  </Button>
                ) : null}
              </div>
            )}
          </ScrollArea>
        </div>

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
    </TooltipProvider>
  );
};
