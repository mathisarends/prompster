import { Search } from "lucide-react";

import type { SpotifyTrackResponse } from "@/api/generated/model";
import { EmptySearchState } from "@/components/deck/search-panel/empty-search-state";
import { SearchResultsSkeleton } from "@/components/deck/search-panel/search-results-skeleton";
import { TrackResultRow } from "@/components/deck/search-panel/track-result-row";

type SearchPanelContentProps = {
  canSearch: boolean;
  isLoading: boolean;
  isError: boolean;
  tracks: SpotifyTrackResponse[];
  isAdding: boolean;
  addingTrackId?: string | null;
  activeTrackId?: string | null;
  isPlaying?: boolean;
  onAddTrack: (track: SpotifyTrackResponse) => void;
  onPreviewTrack: (track: SpotifyTrackResponse) => void;
};

export const SearchPanelContent = ({
  canSearch,
  isLoading,
  isError,
  tracks,
  isAdding,
  addingTrackId,
  activeTrackId,
  isPlaying = false,
  onAddTrack,
  onPreviewTrack,
}: SearchPanelContentProps) => {
  if (!canSearch) {
    return (
      <EmptySearchState
        icon={Search}
        text="Fang an zu tippen, um bei Spotify zu suchen."
      />
    );
  }

  if (isLoading) {
    return <SearchResultsSkeleton />;
  }

  if (isError) {
    return (
      <EmptySearchState icon={Search} text="Spotify-Suche nicht verfügbar." />
    );
  }

  if (tracks.length === 0) {
    return <EmptySearchState icon={Search} text="Keine Treffer bei Spotify." />;
  }

  return (
    <div className="space-y-1">
      {tracks.map((track) => (
        <TrackResultRow
          key={track.id}
          track={track}
          isAdding={isAdding && addingTrackId === track.id}
          disabled={isAdding}
          isActive={activeTrackId === track.id}
          isPlaying={isPlaying}
          onAdd={() => onAddTrack(track)}
          onTogglePreview={() => onPreviewTrack(track)}
        />
      ))}
    </div>
  );
};
