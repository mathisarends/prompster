import { useEffect, useMemo, useState } from "react";
import {
  Check,
  ListMusic,
  Music,
  Plus,
  Search,
  Users,
  X,
} from "lucide-react";

import { useSearchSpotify } from "@/api/generated/spotify/spotify";
import { SpotifySearchType } from "@/api/generated/model";
import type {
  SpotifyArtistResponse,
  SpotifyPlaylistResponse,
} from "@/api/generated/model";
import { useDebouncedValue } from "@/shared/hooks/useDebouncedValue";
import { cn } from "@/shared/lib/utils";

// How closely the agent should stick to a referenced playlist. UI-only for now —
// these drafts are kept in local state and never sent anywhere.
export type ReferenceAdherence = "loose" | "balanced" | "strict";

export type PlaylistReferenceDraft = {
  spotifyPlaylistId: string;
  name: string;
  owner?: string | null;
  coverUrl?: string | null;
  totalTracks?: number | null;
  adherence: ReferenceAdherence;
};

export type ArtistReferenceDraft = {
  spotifyArtistId: string;
  name: string;
  imageUrl?: string | null;
  genres: string[];
  followers?: number | null;
};

export type ReferenceSelection = {
  playlists: PlaylistReferenceDraft[];
  artists: ArtistReferenceDraft[];
};

type OnboardingReferencesStepProps = {
  disabled?: boolean;
  className?: string;
  onSelectionChange?: (selection: ReferenceSelection) => void;
};

type ResultFilter = "all" | "playlists" | "artists";

const FILTER_OPTIONS: { value: ResultFilter; label: string }[] = [
  { value: "all", label: "Alle" },
  { value: "playlists", label: "Playlists" },
  { value: "artists", label: "Artists" },
];

const ADHERENCE_OPTIONS: {
  value: ReferenceAdherence;
  label: string;
  hint: string;
}[] = [
  { value: "loose", label: "Locker", hint: "Nur als grobe Inspiration" },
  { value: "balanced", label: "Ausgewogen", hint: "Stil & Stimmung übernehmen" },
  { value: "strict", label: "Streng", hint: "Eng am Original bleiben" },
];

const MIN_QUERY_LENGTH = 2;
const SEARCH_DEBOUNCE_MS = 200;

const numberFormat = new Intl.NumberFormat("de-DE");

export const OnboardingReferencesStep = ({
  disabled = false,
  className,
  onSelectionChange,
}: OnboardingReferencesStepProps) => {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<ResultFilter>("all");
  const [playlists, setPlaylists] = useState<PlaylistReferenceDraft[]>([]);
  const [artists, setArtists] = useState<ArtistReferenceDraft[]>([]);

  const debouncedQuery = useDebouncedValue(query.trim(), SEARCH_DEBOUNCE_MS);
  const canSearch = debouncedQuery.length >= MIN_QUERY_LENGTH;

  const searchParams = useMemo(
    () => ({
      query: debouncedQuery || "_",
      limit: 6,
      types: [SpotifySearchType.playlist, SpotifySearchType.artist],
    }),
    [debouncedQuery],
  );

  const search = useSearchSpotify(searchParams, {
    query: { enabled: canSearch, staleTime: 30_000 },
  });

  useEffect(() => {
    onSelectionChange?.({ playlists, artists });
  }, [playlists, artists, onSelectionChange]);

  const addedPlaylistIds = useMemo(
    () => new Set(playlists.map((playlist) => playlist.spotifyPlaylistId)),
    [playlists],
  );
  const addedArtistIds = useMemo(
    () => new Set(artists.map((artist) => artist.spotifyArtistId)),
    [artists],
  );

  const resultPlaylists =
    filter === "artists" ? [] : (search.data?.playlists ?? []);
  const resultArtists =
    filter === "playlists" ? [] : (search.data?.artists ?? []);
  const hasResults = resultPlaylists.length > 0 || resultArtists.length > 0;
  const referenceCount = playlists.length + artists.length;

  const addPlaylist = (playlist: SpotifyPlaylistResponse) => {
    if (addedPlaylistIds.has(playlist.id)) return;
    setPlaylists((current) => [
      ...current,
      {
        spotifyPlaylistId: playlist.id,
        name: playlist.name,
        owner: playlist.owner,
        coverUrl: playlist.coverUrl,
        totalTracks: playlist.totalTracks,
        adherence: "balanced",
      },
    ]);
  };

  const addArtist = (artist: SpotifyArtistResponse) => {
    if (addedArtistIds.has(artist.id)) return;
    setArtists((current) => [
      ...current,
      {
        spotifyArtistId: artist.id,
        name: artist.name,
        imageUrl: artist.imageUrl,
        genres: artist.genres ?? [],
        followers: artist.followers,
      },
    ]);
  };

  const removePlaylist = (id: string) =>
    setPlaylists((current) =>
      current.filter((playlist) => playlist.spotifyPlaylistId !== id),
    );

  const removeArtist = (id: string) =>
    setArtists((current) =>
      current.filter((artist) => artist.spotifyArtistId !== id),
    );

  const setPlaylistAdherence = (id: string, adherence: ReferenceAdherence) =>
    setPlaylists((current) =>
      current.map((playlist) =>
        playlist.spotifyPlaylistId === id
          ? { ...playlist, adherence }
          : playlist,
      ),
    );

  return (
    <div className={cn("flex min-h-0 flex-1 flex-col", className)}>
      <div className="shrink-0 space-y-4 px-7 pt-8">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2.5">
            <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-primary/15 text-[11px] font-semibold text-primary">
              <ListMusic className="size-3" />
            </span>
            <h3 className="text-base font-medium leading-snug text-foreground/90">
              Referenzen{" "}
              <span className="text-muted-foreground">(optional)</span>
            </h3>
          </div>
          <p className="pl-[1.875rem] text-sm leading-relaxed text-muted-foreground">
            Suche Playlists und Artists, an denen sich der Agent orientieren
            soll. Bei Playlists legst du fest, wie eng er sich daran hält.
          </p>
        </div>

        <div className="space-y-3">
          <label
            htmlFor="reference-search"
            className="flex h-11 items-center gap-2.5 rounded-full border border-border/60 bg-card/40 px-4 text-sm backdrop-blur-sm transition-colors focus-within:border-primary/60 focus-within:bg-primary/[0.06]"
          >
            <Search className="size-4 shrink-0 text-muted-foreground" />
            <input
              id="reference-search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Playlist oder Artist suchen…"
              disabled={disabled}
              className="h-full min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
          </label>

          <div className="flex items-center justify-between gap-3">
            <div className="flex gap-1.5">
              {FILTER_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => setFilter(option.value)}
                  className={cn(
                    "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                    filter === option.value
                      ? "border-primary/40 bg-primary/15 text-foreground"
                      : "border-border/50 bg-card/30 text-muted-foreground hover:text-foreground",
                  )}
                >
                  {option.label}
                </button>
              ))}
            </div>
            {referenceCount > 0 ? (
              <p className="text-xs font-medium tabular-nums text-muted-foreground">
                {referenceCount} ausgewählt
              </p>
            ) : null}
          </div>
        </div>
      </div>

      <div className="prompster-scrollbar flex min-h-0 flex-1 flex-col gap-8 overflow-y-auto px-7 py-7">
        <SearchResults
          canSearch={canSearch}
          isLoading={search.isLoading}
          isError={search.isError}
          hasResults={hasResults}
          playlists={resultPlaylists}
          artists={resultArtists}
          addedPlaylistIds={addedPlaylistIds}
          addedArtistIds={addedArtistIds}
          onAddPlaylist={addPlaylist}
          onAddArtist={addArtist}
        />

        {referenceCount > 0 ? (
          <div className="space-y-5">
            <div className="h-px bg-white/[0.06]" />

            {playlists.length > 0 ? (
              <div className="space-y-3">
                <SectionLabel
                  icon={ListMusic}
                  label="Playlist-Referenzen"
                  count={playlists.length}
                />
                <div className="space-y-3">
                  {playlists.map((playlist) => (
                    <PlaylistReferenceCard
                      key={playlist.spotifyPlaylistId}
                      playlist={playlist}
                      disabled={disabled}
                      onRemove={() =>
                        removePlaylist(playlist.spotifyPlaylistId)
                      }
                      onAdherenceChange={(adherence) =>
                        setPlaylistAdherence(
                          playlist.spotifyPlaylistId,
                          adherence,
                        )
                      }
                    />
                  ))}
                </div>
              </div>
            ) : null}

            {artists.length > 0 ? (
              <div className="space-y-3">
                <SectionLabel
                  icon={Users}
                  label="Artist-Referenzen"
                  count={artists.length}
                />
                <div className="flex flex-wrap gap-2.5">
                  {artists.map((artist) => (
                    <ArtistReferenceChip
                      key={artist.spotifyArtistId}
                      artist={artist}
                      disabled={disabled}
                      onRemove={() => removeArtist(artist.spotifyArtistId)}
                    />
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
};

type SearchResultsProps = {
  canSearch: boolean;
  isLoading: boolean;
  isError: boolean;
  hasResults: boolean;
  playlists: SpotifyPlaylistResponse[];
  artists: SpotifyArtistResponse[];
  addedPlaylistIds: Set<string>;
  addedArtistIds: Set<string>;
  onAddPlaylist: (playlist: SpotifyPlaylistResponse) => void;
  onAddArtist: (artist: SpotifyArtistResponse) => void;
};

const SearchResults = ({
  canSearch,
  isLoading,
  isError,
  hasResults,
  playlists,
  artists,
  addedPlaylistIds,
  addedArtistIds,
  onAddPlaylist,
  onAddArtist,
}: SearchResultsProps) => {
  if (!canSearch) {
    return (
      <EmptyHint>
        Tippe mindestens 2 Zeichen, um Playlists oder Artists zu suchen.
      </EmptyHint>
    );
  }
  if (isLoading) {
    return <EmptyHint>Suche bei Spotify…</EmptyHint>;
  }
  if (isError) {
    return <EmptyHint>Spotify-Suche gerade nicht verfügbar.</EmptyHint>;
  }
  if (!hasResults) {
    return <EmptyHint>Keine Treffer.</EmptyHint>;
  }

  return (
    <div className="space-y-2">
      {playlists.map((playlist) => (
        <SearchResultRow
          key={`p-${playlist.id}`}
          imageUrl={playlist.coverUrl}
          rounded={false}
          title={playlist.name}
          subtitle={playlist.owner ?? undefined}
          added={addedPlaylistIds.has(playlist.id)}
          onAdd={() => onAddPlaylist(playlist)}
        />
      ))}
      {artists.map((artist) => (
        <SearchResultRow
          key={`a-${artist.id}`}
          imageUrl={artist.imageUrl}
          rounded
          title={artist.name}
          subtitle={artist.genres?.slice(0, 2).join(", ") || undefined}
          added={addedArtistIds.has(artist.id)}
          onAdd={() => onAddArtist(artist)}
        />
      ))}
    </div>
  );
};

type SearchResultRowProps = {
  imageUrl?: string | null;
  rounded: boolean;
  title: string;
  subtitle?: string;
  added: boolean;
  onAdd: () => void;
};

const SearchResultRow = ({
  imageUrl,
  rounded,
  title,
  subtitle,
  added,
  onAdd,
}: SearchResultRowProps) => (
  <button
    type="button"
    onClick={onAdd}
    disabled={added}
    className={cn(
      "group/row flex w-full items-center gap-3 rounded-lg border border-transparent px-2.5 py-2 text-left transition-colors hover:bg-white/[0.05] disabled:cursor-default disabled:hover:bg-transparent",
    )}
  >
    <ReferenceThumb imageUrl={imageUrl} rounded={rounded} />
    <div className="min-w-0 flex-1">
      <p className="truncate text-sm font-medium leading-tight">{title}</p>
      {subtitle ? (
        <p className="mt-0.5 truncate text-xs text-muted-foreground">
          {subtitle}
        </p>
      ) : null}
    </div>
    {added ? (
      <span className="flex items-center gap-1 text-xs font-medium text-primary">
        <Check className="size-3.5" />
        Hinzugefügt
      </span>
    ) : (
      <Plus className="size-4 text-muted-foreground opacity-0 transition-opacity group-hover/row:opacity-100" />
    )}
  </button>
);

type PlaylistReferenceCardProps = {
  playlist: PlaylistReferenceDraft;
  disabled: boolean;
  onRemove: () => void;
  onAdherenceChange: (adherence: ReferenceAdherence) => void;
};

const PlaylistReferenceCard = ({
  playlist,
  disabled,
  onRemove,
  onAdherenceChange,
}: PlaylistReferenceCardProps) => {
  const activeHint = ADHERENCE_OPTIONS.find(
    (option) => option.value === playlist.adherence,
  )?.hint;

  return (
    <div className="space-y-3 rounded-xl border border-border/50 bg-card/30 p-3.5">
      <div className="flex items-center gap-3">
        <ReferenceThumb imageUrl={playlist.coverUrl} rounded={false} />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium leading-tight">
            {playlist.name}
          </p>
          <p className="mt-0.5 truncate text-xs text-muted-foreground">
            {[playlist.owner, formatTrackCount(playlist.totalTracks)]
              .filter(Boolean)
              .join(" · ") || "Playlist"}
          </p>
        </div>
        <RemoveButton onClick={onRemove} disabled={disabled} label="Playlist" />
      </div>

      <div className="space-y-1.5">
        <div className="flex gap-1.5 rounded-lg border border-border/40 bg-[#070b0c]/60 p-1">
          {ADHERENCE_OPTIONS.map((option) => {
            const active = option.value === playlist.adherence;
            return (
              <button
                key={option.value}
                type="button"
                disabled={disabled}
                onClick={() => onAdherenceChange(option.value)}
                className={cn(
                  "flex-1 rounded-md px-2 py-1.5 text-xs font-medium transition-colors disabled:pointer-events-none",
                  active
                    ? "bg-primary/20 text-foreground shadow-[0_2px_16px_-8px_hsl(141_73%_42%/0.6)]"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {option.label}
              </button>
            );
          })}
        </div>
        {activeHint ? (
          <p className="pl-1 text-[11px] text-muted-foreground">{activeHint}</p>
        ) : null}
      </div>
    </div>
  );
};

type ArtistReferenceChipProps = {
  artist: ArtistReferenceDraft;
  disabled: boolean;
  onRemove: () => void;
};

const ArtistReferenceChip = ({
  artist,
  disabled,
  onRemove,
}: ArtistReferenceChipProps) => (
  <div className="flex items-center gap-2.5 rounded-full border border-border/50 bg-card/40 py-1.5 pl-1.5 pr-2.5">
    <ReferenceThumb imageUrl={artist.imageUrl} rounded size="sm" />
    <span className="max-w-40 truncate text-sm font-medium">{artist.name}</span>
    <RemoveButton onClick={onRemove} disabled={disabled} label="Artist" />
  </div>
);

type ReferenceThumbProps = {
  imageUrl?: string | null;
  rounded: boolean;
  size?: "sm" | "md";
};

const ReferenceThumb = ({
  imageUrl,
  rounded,
  size = "md",
}: ReferenceThumbProps) => (
  <div
    className={cn(
      "grid shrink-0 place-items-center overflow-hidden bg-white/[0.06] text-muted-foreground ring-1 ring-white/[0.04]",
      size === "sm" ? "size-7" : "size-10",
      rounded ? "rounded-full" : "rounded-md",
    )}
  >
    {imageUrl ? (
      <img
        src={imageUrl}
        alt=""
        className="h-full w-full object-cover"
        loading="lazy"
      />
    ) : (
      <Music className={size === "sm" ? "size-3.5" : "size-4"} />
    )}
  </div>
);

type RemoveButtonProps = {
  onClick: () => void;
  disabled: boolean;
  label: string;
};

const RemoveButton = ({ onClick, disabled, label }: RemoveButtonProps) => (
  <button
    type="button"
    onClick={onClick}
    disabled={disabled}
    aria-label={`${label} entfernen`}
    className="grid size-6 shrink-0 place-items-center rounded-full text-muted-foreground transition-colors hover:bg-white/[0.08] hover:text-foreground disabled:pointer-events-none disabled:opacity-50"
  >
    <X className="size-3.5" />
  </button>
);

const SectionLabel = ({
  icon: Icon,
  label,
  count,
}: {
  icon: typeof ListMusic;
  label: string;
  count: number;
}) => (
  <p className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">
    <Icon className="size-3.5" />
    {label}
    <span className="tabular-nums text-muted-foreground/70">{count}</span>
  </p>
);

const EmptyHint = ({ children }: { children: React.ReactNode }) => (
  <div className="py-10 text-center text-sm text-muted-foreground">
    {children}
  </div>
);

const formatTrackCount = (total?: number | null) =>
  typeof total === "number" ? `${numberFormat.format(total)} Songs` : null;
