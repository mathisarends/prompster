import { useMemo, useState } from "react";
import { Play, Search, X } from "lucide-react";

export type PlaylistTrack = {
  id: string;
  title: string;
  artist: string;
  year: string;
  genre: string;
  coverFrom: string;
  coverTo: string;
  coverUrl?: string;
};

type TrackPlaylistProps = {
  initialTracks: PlaylistTrack[];
};

export const TrackPlaylist = ({ initialTracks }: TrackPlaylistProps) => {
  const [query, setQuery] = useState("");
  const [tracks, setTracks] = useState(initialTracks);
  const tableGrid = "grid-cols-[52px_minmax(0,1fr)_110px_120px_52px]";

  const filteredTracks = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) {
      return tracks;
    }

    return tracks.filter((track) =>
      `${track.title} ${track.artist} ${track.year} ${track.genre}`
        .toLowerCase()
        .includes(normalized),
    );
  }, [query, tracks]);

  const removeTrack = (trackId: string) => {
    setTracks((prev) => prev.filter((track) => track.id !== trackId));
  };

  return (
    <>
      <div className="border-b border-[var(--beatline-border)] px-3 py-3">
        <label className="relative block">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--beatline-subtle)]"
            size={16}
          />
          <input
            className="w-full rounded-md border border-[var(--beatline-border)] bg-[var(--beatline-bg)] py-2 pl-9 pr-3 text-sm text-[var(--beatline-text)] outline-none placeholder:text-[var(--beatline-subtle)]"
            placeholder="Playlist durchsuchen: Titel, Artist, Jahr, Genre..."
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
      </div>

      <div className="min-h-0 flex-1 overflow-auto py-2">
        <div
          className={`grid ${tableGrid} items-center px-3 py-2 text-xs font-semibold uppercase tracking-[0.12em] text-[var(--beatline-muted)]`}
        >
          <span className="justify-self-center">#</span>
          <span>Titel</span>
          <span>Jahr</span>
          <span>Genre</span>
          <span />
        </div>

        {filteredTracks.map((track, idx) => (
          <div
            key={track.id}
            className={`group grid ${tableGrid} items-center rounded-md border border-transparent px-3 py-2 ${
              idx === 0
                ? "bg-[var(--beatline-highlight)]"
                : "hover:bg-[var(--beatline-highlight)]"
            }`}
          >
            <div className="relative grid place-items-center text-sm tabular-nums text-[var(--beatline-muted)]">
              <span className="group-hover:hidden">{idx + 1}</span>
              <button
                className="absolute hidden h-7 w-7 place-items-center rounded-full text-[var(--beatline-text)] transition-colors hover:text-[var(--beatline-gold)] group-hover:grid"
                type="button"
                aria-label={`${track.title} abspielen`}
              >
                <Play size={15} fill="currentColor" />
              </button>
            </div>

            <div className="flex min-w-0 items-center gap-3">
              <div
                className="relative grid h-10 w-10 place-items-center overflow-hidden rounded border border-[var(--beatline-border)] text-[11px] font-semibold uppercase text-white"
                style={{
                  backgroundImage: `linear-gradient(140deg, ${track.coverFrom}, ${track.coverTo})`,
                }}
              >
                {track.coverUrl ? (
                  <img
                    src={track.coverUrl}
                    alt={`${track.title} Cover`}
                    className="absolute inset-0 h-full w-full object-cover"
                    loading="lazy"
                    onError={(event) => {
                      event.currentTarget.style.display = "none";
                    }}
                  />
                ) : null}
                <span>{track.artist.slice(0, 2)}</span>
              </div>
              <div className="min-w-0">
                <p className="truncate font-semibold">{track.title}</p>
                <p className="truncate text-sm text-[var(--beatline-muted)]">
                  {track.artist}
                </p>
              </div>
            </div>

            <span className="text-sm">{track.year}</span>
            <span className="text-xs uppercase tracking-[0.08em] text-[var(--beatline-muted)]">
              {track.genre}
            </span>

            <div className="flex items-center justify-end text-[var(--beatline-muted)]">
              <button
                className="grid h-7 w-7 place-items-center rounded-full border border-[var(--beatline-border)] transition-colors hover:border-[var(--beatline-gold-dark)] hover:text-[var(--beatline-gold)]"
                type="button"
                onClick={() => removeTrack(track.id)}
                aria-label={`${track.title} entfernen`}
              >
                <X size={14} />
              </button>
            </div>
          </div>
        ))}

        {filteredTracks.length === 0 && (
          <div className="px-3 py-8 text-center text-sm text-[var(--beatline-muted)]">
            Keine Treffer in der Playlist.
          </div>
        )}
      </div>
    </>
  );
};
