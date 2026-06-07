import { useMemo, useState, type Ref } from "react";

import { useSearchSpotify } from "@/api/generated/spotify/spotify";
import { SpotifySearchType } from "@/api/generated/model";
import type { SpotifyTrackResponse } from "@/api/generated/model";
import { SearchPanelContent } from "@/features/deck/components/search-panel/search-panel-content";
import { useDebouncedValue } from "@/shared/hooks/useDebouncedValue";

type SpotifyTrackSearchPanelProps = {
  panelRef?: Ref<HTMLDivElement>;
  query: string;
  isAdding?: boolean;
  addingTrackId?: string | null;
  activeTrackId?: string | null;
  isPlaying?: boolean;
  onAddTrack: (track: SpotifyTrackResponse) => Promise<void> | void;
  onPreviewTrack?: (track: SpotifyTrackResponse) => void;
  onTogglePreviewPlayPause?: () => void;
};

type SpotifyTrackSearchResultsProps = Omit<
  SpotifyTrackSearchPanelProps,
  "panelRef"
>;

const minSearchLength = 2;
const searchDebounceMs = 220;

export const SpotifyTrackSearchPanel = ({
  panelRef,
  query,
  isAdding = false,
  addingTrackId,
  activeTrackId,
  isPlaying = false,
  onAddTrack,
  onPreviewTrack,
  onTogglePreviewPlayPause,
}: SpotifyTrackSearchPanelProps) => {
  return (
    <section
      ref={panelRef}
      className="mb-4 overflow-hidden rounded-md border border-primary/20 bg-popover/95 shadow-[0_22px_54px_hsl(195_45%_3%/0.62)] ring-1 ring-primary/10 animate-in fade-in-0 slide-in-from-top-2 duration-150"
    >
      <div className="prompster-scrollbar max-h-[min(42vh,27rem)] overflow-y-auto px-3 pr-1">
        <div className="space-y-4 py-3">
          <SpotifyTrackSearchResults
            query={query}
            isAdding={isAdding}
            addingTrackId={addingTrackId}
            activeTrackId={activeTrackId}
            isPlaying={isPlaying}
            onAddTrack={onAddTrack}
            onPreviewTrack={onPreviewTrack}
            onTogglePreviewPlayPause={onTogglePreviewPlayPause}
          />
        </div>
      </div>
    </section>
  );
};

export const SpotifyTrackSearchResults = ({
  query,
  isAdding = false,
  addingTrackId,
  activeTrackId,
  isPlaying = false,
  onAddTrack,
  onPreviewTrack,
  onTogglePreviewPlayPause,
}: SpotifyTrackSearchResultsProps) => {
  const [addedTrackIds, setAddedTrackIds] = useState<Set<string>>(
    () => new Set(),
  );
  const debouncedQuery = useDebouncedValue(query.trim(), searchDebounceMs);

  const canSearch = debouncedQuery.length >= minSearchLength;

  const searchParams = useMemo(
    () => ({
      query: debouncedQuery || "_",
      limit: 8,
      types: [SpotifySearchType.track],
    }),
    [debouncedQuery],
  );

  const search = useSearchSpotify(searchParams, {
    query: {
      enabled: canSearch,
      staleTime: 30_000,
    },
  });

  const tracks = useMemo(
    () =>
      (search.data?.tracks ?? []).filter(
        (track) => !addedTrackIds.has(track.id),
      ),
    [addedTrackIds, search.data?.tracks],
  );

  const addTrack = async (track: SpotifyTrackResponse) => {
    await onAddTrack(track);
    setAddedTrackIds((current) => {
      const next = new Set(current);
      next.add(track.id);
      return next;
    });
  };

  return (
    <SearchPanelContent
      canSearch={canSearch}
      isLoading={search.isLoading}
      isError={search.isError}
      tracks={tracks}
      isAdding={isAdding}
      addingTrackId={addingTrackId}
      activeTrackId={activeTrackId}
      isPlaying={isPlaying}
      onAddTrack={(track) => {
        void addTrack(track);
      }}
      onPreviewTrack={
        onPreviewTrack
          ? (track) => {
              if (activeTrackId === track.id) {
                onTogglePreviewPlayPause?.();
                return;
              }
              onPreviewTrack(track);
            }
          : undefined
      }
    />
  );
};
