import { useMemo, useState, type ReactNode, type Ref } from "react";
import { Loader2, Plus, Search } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { useSearchSpotify } from "@/api/generated/spotify/spotify";
import { SpotifySearchType } from "@/api/generated/model";
import type { SpotifyTrackResponse } from "@/api/generated/model";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

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
      <div className="border-b border-white/[0.07] px-3 py-2.5">
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold tracking-tight">
            Spotify-Suche
          </h3>
        </div>
      </div>

      <ScrollArea className="max-h-[min(42vh,27rem)] px-3">
        <div className="space-y-4 py-3">
          {!canSearch ? (
            <EmptySearchState icon={Search} text="Mindestens zwei Zeichen." />
          ) : search.isLoading ? (
            <EmptySearchState icon={Loader2} text="Spotify sucht..." spin />
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
      </ScrollArea>
    </section>
  );
};

type EmptySearchStateProps = {
  icon: LucideIcon;
  text: string;
  spin?: boolean;
};

const EmptySearchState = ({
  icon: Icon,
  text,
  spin,
}: EmptySearchStateProps) => (
  <div className="flex min-h-28 flex-col items-center justify-center gap-2 text-center text-sm text-muted-foreground">
    <Icon className={cn("size-4", spin ? "animate-spin" : null)} />
    <p>{text}</p>
  </div>
);

type TrackResultRowProps = {
  track: SpotifyTrackResponse;
  isAdding: boolean;
  disabled: boolean;
  onAdd: () => void;
};

const TrackResultRow = ({
  track,
  isAdding,
  disabled,
  onAdd,
}: TrackResultRowProps) => (
  <div className="grid grid-cols-[40px_minmax(0,1fr)_auto] items-center gap-3 rounded-md px-2 py-2 transition-colors hover:bg-white/[0.04]">
    <Cover src={track.coverUrl} alt={`${track.title} Cover`} />
    <div className="min-w-0">
      <p className="truncate text-sm font-semibold leading-tight">
        {track.title}
      </p>
      <p className="mt-0.5 truncate text-xs text-muted-foreground">
        {track.artist}
        {track.album ? ` · ${track.album}` : ""}
        {track.year ? ` · ${track.year}` : ""}
      </p>
    </div>
    <Tooltip>
      <TooltipTrigger
        render={
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            aria-label={`${track.title} hinzufügen`}
            disabled={disabled}
            onClick={onAdd}
          >
            {isAdding ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Plus className="size-4" />
            )}
          </Button>
        }
      />
      <TooltipContent side="left" sideOffset={8}>
        {track.title} hinzufügen
      </TooltipContent>
    </Tooltip>
  </div>
);

type CoverProps = {
  src?: string | null;
  alt: string;
  fallback?: ReactNode;
};

const Cover = ({ src, alt, fallback }: CoverProps) => (
  <div className="grid size-10 shrink-0 place-items-center overflow-hidden rounded-[4px] bg-white/[0.06] text-muted-foreground shadow-sm ring-1 ring-white/[0.04]">
    {src ? (
      <img
        src={src}
        alt={alt}
        className="h-full w-full object-cover"
        loading="lazy"
      />
    ) : (
      fallback
    )}
  </div>
);
