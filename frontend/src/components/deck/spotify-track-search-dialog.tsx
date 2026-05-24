import { Children, useEffect, useMemo, useState, type ReactNode } from "react";
import { Loader2, Plus, Search } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { useSearchSpotify } from "@/api/generated/spotify/spotify";
import { SpotifySearchType } from "@/api/generated/model";
import type { SpotifyTrackResponse } from "@/api/generated/model";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { SearchBar } from "@/components/deck/search-bar";
import { cn } from "@/lib/utils";

type SpotifyTrackSearchDialogProps = {
  open: boolean;
  initialQuery?: string;
  isAdding?: boolean;
  addingTrackId?: string | null;
  onOpenChange: (open: boolean) => void;
  onAddTrack: (track: SpotifyTrackResponse) => Promise<void> | void;
};

const minSearchLength = 2;

export const SpotifyTrackSearchDialog = ({
  open,
  initialQuery = "",
  isAdding = false,
  addingTrackId,
  onOpenChange,
  onAddTrack,
}: SpotifyTrackSearchDialogProps) => {
  const [query, setQuery] = useState(initialQuery);
  const normalizedQuery = query.trim();
  const canSearch = normalizedQuery.length >= minSearchLength;

  useEffect(() => {
    if (open) setQuery(initialQuery);
  }, [initialQuery, open]);

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
      enabled: open && canSearch,
      staleTime: 30_000,
    },
  });

  const tracks = search.data?.tracks ?? [];
  const hasResults = tracks.length > 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="top-[8%] flex max-h-[min(760px,calc(100vh-3rem))] max-w-2xl flex-col overflow-hidden rounded-lg">
        <div className="border-b border-white/[0.07] px-4 py-3">
          <DialogTitle>Spotify durchsuchen</DialogTitle>
          <DialogDescription className="mt-1">
            Songs zur Playlist hinzufügen.
          </DialogDescription>
        </div>

        <div className="px-4 pt-4">
          <SearchBar
            value={query}
            autoFocus
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Titel oder Artist suchen..."
            containerClassName="px-0"
            inputClassName="h-11 bg-white/[0.06] text-base"
          />
        </div>

        <ScrollArea className="min-h-0 flex-1 px-4">
          <div className="space-y-5 py-4">
            {!canSearch ? (
              <EmptySearchState
                icon={Search}
                text="Gib mindestens zwei Zeichen ein."
              />
            ) : search.isLoading ? (
              <EmptySearchState
                icon={Loader2}
                text="Spotify wird durchsucht..."
                spin
              />
            ) : search.isError ? (
              <EmptySearchState
                icon={Search}
                text="Spotify-Suche konnte nicht geladen werden."
              />
            ) : !hasResults ? (
              <EmptySearchState
                icon={Search}
                text="Keine Treffer bei Spotify. Wir können es mit einer anderen Schreibweise suchen."
              />
            ) : (
              <ResultGroup title="Songs" emptyText="Keine Songs gefunden.">
                {tracks.map((track) => (
                  <TrackResultRow
                    key={track.id}
                    track={track}
                    isAdding={isAdding && addingTrackId === track.id}
                    disabled={isAdding}
                    onAdd={() => onAddTrack(track)}
                  />
                ))}
              </ResultGroup>
            )}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
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
  <div className="flex min-h-48 flex-col items-center justify-center gap-3 text-center text-sm text-muted-foreground">
    <Icon className={cn("size-5", spin ? "animate-spin" : null)} />
    <p>{text}</p>
  </div>
);

type ResultGroupProps = {
  title: string;
  emptyText: string;
  children: ReactNode;
};

const ResultGroup = ({ title, emptyText, children }: ResultGroupProps) => {
  const items = useMemo(() => Children.toArray(children), [children]);
  return (
    <section className="space-y-2">
      <div className="flex items-center justify-between gap-3 text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
        <h3>{title}</h3>
        <span>{items.length}</span>
      </div>
      {items.length > 0 ? (
        <div className="space-y-1">{items}</div>
      ) : (
        <p className="rounded-md border border-white/[0.06] px-3 py-3 text-sm text-muted-foreground">
          {emptyText}
        </p>
      )}
    </section>
  );
};

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
  <div className="grid grid-cols-[44px_minmax(0,1fr)_auto] items-center gap-3 rounded-md px-2 py-2 hover:bg-white/[0.04]">
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
    <Button
      type="button"
      variant="ghost"
      size="icon-sm"
      aria-label={`${track.title} hinzufügen`}
      title="Song hinzufügen"
      disabled={disabled}
      onClick={onAdd}
    >
      {isAdding ? (
        <Loader2 className="size-4 animate-spin" />
      ) : (
        <Plus className="size-4" />
      )}
    </Button>
  </div>
);

type CoverProps = {
  src?: string | null;
  alt: string;
  fallback?: ReactNode;
};

const Cover = ({ src, alt, fallback }: CoverProps) => (
  <div className="grid size-11 shrink-0 place-items-center overflow-hidden rounded-[4px] bg-white/[0.06] text-muted-foreground shadow-sm">
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
