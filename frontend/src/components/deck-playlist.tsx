import { useEffect, useMemo, useState } from "react";
import { Play, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { SearchBar } from "@/components/search-bar";
import { cn } from "@/lib/utils";
import { mockTracks, type PlaylistTrack } from "@/lib/mockTracks";

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

      <div className="grid grid-cols-[44px_minmax(0,1fr)_72px_40px] items-center px-3 pb-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground/70">
        <span className="justify-self-center">#</span>
        <span>Titel</span>
        <span>Jahr</span>
        <span />
      </div>

      <ScrollArea className="min-h-0 flex-1 pr-2">
        <div className="space-y-1.5 pb-3">
          {filteredTracks.map((track, index) => (
            <div
              key={track.id}
              className={cn(
                "group grid grid-cols-[44px_minmax(0,1fr)_72px_40px] items-center rounded-xl px-3 py-2.5 transition-colors",
                index === 0 ? "bg-emerald-500/10" : "hover:bg-white/[0.04]",
              )}
            >
              <div className="relative grid place-items-center text-xs tabular-nums text-muted-foreground">
                <span className="group-hover:hidden">{index + 1}</span>
                <Button
                  size="icon-xs"
                  variant="ghost"
                  className="absolute hidden text-foreground group-hover:inline-flex"
                  aria-label={`${track.title} abspielen`}
                >
                  <Play className="size-3.5 fill-current" />
                </Button>
              </div>

              <div className="flex min-w-0 items-center gap-3">
                <div className="h-10 w-10 overflow-hidden rounded-lg bg-white/[0.06] shadow-sm">
                  <img
                    src={track.coverUrl}
                    alt={`${track.title} Cover`}
                    className="h-full w-full object-cover"
                    loading="lazy"
                  />
                </div>
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold leading-tight text-foreground">
                    {track.title}
                  </p>
                  <p className="mt-0.5 truncate text-xs text-muted-foreground">
                    {track.artist}
                  </p>
                </div>
              </div>

              <span className="text-xs font-medium tabular-nums text-foreground/80">
                {track.year}
              </span>

              <div className="flex items-center justify-end">
                <Button
                  size="icon-xs"
                  variant="ghost"
                  className="text-muted-foreground hover:text-foreground"
                  aria-label={`${track.title} entfernen`}
                  onClick={() => removeTrack(track.id)}
                >
                  <X className="size-3.5" />
                </Button>
              </div>
            </div>
          ))}
        </div>
        {filteredTracks.length === 0 ? (
          <div className="px-3 py-8 text-center text-sm text-muted-foreground">
            Keine Treffer in der Playlist.
          </div>
        ) : null}
      </ScrollArea>
    </div>
  );
};
