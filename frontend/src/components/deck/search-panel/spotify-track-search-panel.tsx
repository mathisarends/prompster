import { useMemo, useState, type Ref } from "react";
import { Search } from "lucide-react";

import { useSearchSpotify } from "@/api/generated/spotify/spotify";
import { SpotifySearchType } from "@/api/generated/model";
import type { SpotifyTrackResponse } from "@/api/generated/model";
import { EmptySearchState } from "@/components/deck/search-panel/empty-search-state";
import { SearchResultsSkeleton } from "@/components/deck/search-panel/search-results-skeleton";
import { TrackResultRow } from "@/components/deck/search-panel/track-result-row";

type SpotifyTrackSearchPanelProps = {
  panelRef?: Ref<HTMLDivElement>;
  query: string;
  isAdding?: boolean;
  addingTrackId?: string | null;
  onAddTrack: (track: SpotifyTrackResponse) => Promise<void> | void;
};

const minSearchLength = 2;

export const SpotifyTrackSearchPanel = ({
  panelRef,
  query,
  isAdding = false,
  addingTrackId,
  onAddTrack,
}: SpotifyTrackSearchPanelProps) => {
  const [addedTrackIds, setAddedTrackIds] = useState<Set<string>>(
    () => new Set(),
  );
  const normalizedQuery = query.trim();
  const canSearch = normalizedQuery.length >= minSearchLength;

  const searchParams = useMemo(
    () => ({
      query: normalizedQuery || "_",
      limit: 8,
      types: [SpotifySearchType.track],
    }),
    [normalizedQuery],
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
  const hasResults = tracks.length > 0;

  const addTrack = async (track: SpotifyTrackResponse) => {
    await onAddTrack(track);
    setAddedTrackIds((current) => {
      const next = new Set(current);
      next.add(track.id);
      return next;
    });
  };

  return (
    <section
      ref={panelRef}
      className="mb-4 overflow-hidden rounded-md border border-primary/20 bg-popover/95 shadow-[0_22px_54px_hsl(222_52%_4%/0.58)] ring-1 ring-primary/10 animate-in fade-in-0 slide-in-from-top-2 duration-150"
    >
      <div className="prompster-scrollbar max-h-[min(42vh,27rem)] overflow-y-auto px-3 pr-1">
        <div className="space-y-4 py-3">
          {!canSearch ? (
            <EmptySearchState
              icon={Search}
              text="Fang an zu tippen, um bei Spotify zu suchen."
            />
          ) : search.isLoading ? (
            <SearchResultsSkeleton />
          ) : search.isError ? (
            <EmptySearchState
              icon={Search}
              text="Spotify-Suche nicht verfügbar."
            />
          ) : !hasResults ? (
            <EmptySearchState icon={Search} text="Keine Treffer bei Spotify." />
          ) : (
            <div className="space-y-1">
              {tracks.map((track) => (
                <TrackResultRow
                  key={track.id}
                  track={track}
                  isAdding={isAdding && addingTrackId === track.id}
                  disabled={isAdding}
                  onAdd={() => void addTrack(track)}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
};