import { useEffect, useMemo, useRef, useState } from "react";
import { Loader2, Music, Paperclip, Plus, Search } from "lucide-react";

import { useSearchSpotify } from "@/api/generated/spotify/spotify";
import { SpotifySearchType } from "@/api/generated/model";
import type {
  SpotifyArtistResponse,
  SpotifyPlaylistResponse,
  SpotifyTrackResponse,
} from "@/api/generated/model";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

import type { ChatAttachment } from "./attachment-types";
import { parseSpotifyRef } from "./spotify-id-parser";

type AttachmentPopoverProps = {
  attachments: ChatAttachment[];
  onAdd: (attachment: ChatAttachment) => void;
  disabled?: boolean;
  triggerClassName?: string;
};

const MIN_QUERY_LENGTH = 2;

const trackToAttachment = (track: SpotifyTrackResponse): ChatAttachment => ({
  id: track.id,
  kind: "spotify-track",
  title: track.title,
  subtitle: track.artist,
  imageUrl: track.coverUrl,
  spotifyId: track.id,
});

const playlistToAttachment = (
  playlist: SpotifyPlaylistResponse,
): ChatAttachment => ({
  id: playlist.id,
  kind: "spotify-playlist",
  title: playlist.name,
  subtitle: playlist.owner ?? undefined,
  imageUrl: playlist.coverUrl,
  spotifyId: playlist.id,
});

const artistToAttachment = (artist: SpotifyArtistResponse): ChatAttachment => ({
  id: artist.id,
  kind: "spotify-artist",
  title: artist.name,
  subtitle: artist.genres?.slice(0, 2).join(", ") || undefined,
  imageUrl: artist.imageUrl,
  spotifyId: artist.id,
});

type ResultRowProps = {
  attachment: ChatAttachment;
  isAttached: boolean;
  onPick: () => void;
};

const ResultRow = ({ attachment, isAttached, onPick }: ResultRowProps) => (
  <button
    type="button"
    onClick={onPick}
    disabled={isAttached}
    className={cn(
      "group/row flex w-full items-center gap-2.5 rounded-md px-2 py-1.5 text-left transition-colors hover:bg-white/[0.05] disabled:cursor-not-allowed disabled:opacity-50",
    )}
  >
    <div
      className={cn(
        "grid size-9 shrink-0 place-items-center overflow-hidden bg-white/[0.06] text-muted-foreground ring-1 ring-white/[0.04]",
        attachment.kind === "spotify-artist" ? "rounded-full" : "rounded-[4px]",
      )}
    >
      {attachment.imageUrl ? (
        <img
          src={attachment.imageUrl}
          alt={attachment.title}
          className="h-full w-full object-cover"
          loading="lazy"
        />
      ) : (
        <Music className="size-4" />
      )}
    </div>
    <div className="min-w-0 flex-1">
      <p className="truncate text-[13px] font-medium leading-tight">
        {attachment.title}
      </p>
      {attachment.subtitle && (
        <p className="mt-0.5 truncate text-[11px] text-muted-foreground">
          {attachment.subtitle}
        </p>
      )}
    </div>
    <Plus
      className={cn(
        "size-4 text-muted-foreground transition-opacity",
        isAttached
          ? "opacity-0"
          : "opacity-0 group-hover/row:opacity-100",
      )}
    />
  </button>
);

const SectionLabel = ({ label }: { label: string }) => (
  <p className="px-2 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground/80">
    {label}
  </p>
);

export const AttachmentPopover = ({
  attachments,
  onAdd,
  disabled,
  triggerClassName,
}: AttachmentPopoverProps) => {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const handleOpenChange = (next: boolean) => {
    setOpen(next);
    if (!next) {
      setQuery("");
      setDebouncedQuery("");
    }
  };

  useEffect(() => {
    if (!open) return;
    const id = window.setTimeout(() => inputRef.current?.focus(), 30);
    return () => window.clearTimeout(id);
  }, [open]);

  useEffect(() => {
    const id = window.setTimeout(() => setDebouncedQuery(query.trim()), 180);
    return () => window.clearTimeout(id);
  }, [query]);

  const parsedRef = useMemo(() => parseSpotifyRef(query), [query]);

  const canSearch = !parsedRef && debouncedQuery.length >= MIN_QUERY_LENGTH;

  const searchParams = useMemo(
    () => ({
      query: debouncedQuery || "_",
      limit: 6,
      types: [
        SpotifySearchType.playlist,
        SpotifySearchType.artist,
        SpotifySearchType.track,
      ],
    }),
    [debouncedQuery],
  );

  const search = useSearchSpotify(searchParams, {
    query: { enabled: open && canSearch, staleTime: 30_000 },
  });

  const attachedKey = useMemo(
    () => new Set(attachments.map((a) => `${a.kind}:${a.id}`)),
    [attachments],
  );

  const pick = (attachment: ChatAttachment) => {
    if (attachedKey.has(`${attachment.kind}:${attachment.id}`)) return;
    onAdd(attachment);
    setQuery("");
    setDebouncedQuery("");
    inputRef.current?.focus();
  };

  const addParsedRef = () => {
    if (!parsedRef) return;
    pick({
      id: parsedRef.id,
      kind: parsedRef.kind,
      title: `Spotify ${parsedRef.kind.replace("spotify-", "")}`,
      subtitle: parsedRef.id,
      spotifyId: parsedRef.id,
    });
  };

  const playlists = search.data?.playlists ?? [];
  const artists = search.data?.artists ?? [];
  const tracks = search.data?.tracks ?? [];
  const hasResults =
    playlists.length > 0 || artists.length > 0 || tracks.length > 0;

  return (
    <Popover open={open} onOpenChange={handleOpenChange}>
      <TooltipProvider delay={300}>
        <Tooltip>
          <TooltipTrigger
            render={
              <PopoverTrigger
                render={
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    disabled={disabled}
                    aria-label="Anhang hinzufügen"
                    className={cn(
                      "shrink-0 rounded-full text-muted-foreground hover:text-foreground",
                      triggerClassName,
                    )}
                  >
                    <Paperclip className="size-4" />
                  </Button>
                }
              />
            }
          />
          <TooltipContent side="top" sideOffset={6} showArrow={false}>
            Anhang hinzufügen
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <PopoverContent
        side="top"
        align="start"
        sideOffset={10}
        className="w-80 p-0"
      >
        <div className="flex items-center gap-2 border-b border-white/[0.06] px-3 py-2.5">
          <Search className="size-4 shrink-0 text-muted-foreground" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && parsedRef) {
                e.preventDefault();
                addParsedRef();
              }
            }}
            placeholder="Spotify suchen oder Link einfügen"
            className="h-7 min-w-0 flex-1 bg-transparent text-[13px] outline-none placeholder:text-muted-foreground/70"
          />
        </div>

        <div className="prompster-scrollbar max-h-80 overflow-y-auto p-1.5">
          {parsedRef ? (
            <button
              type="button"
              onClick={addParsedRef}
              className="flex w-full items-center gap-2.5 rounded-md px-2 py-2 text-left transition-colors hover:bg-white/[0.05]"
            >
              <div className="grid size-9 shrink-0 place-items-center rounded-[4px] bg-primary/15 text-primary ring-1 ring-primary/20">
                <Plus className="size-4" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-[13px] font-medium leading-tight">
                  Spotify-{parsedRef.kind.replace("spotify-", "")} anhängen
                </p>
                <p className="mt-0.5 truncate text-[11px] text-muted-foreground">
                  ID: {parsedRef.id}
                </p>
              </div>
            </button>
          ) : !canSearch ? (
            <div className="px-3 py-6 text-center text-[12px] text-muted-foreground">
              Suche nach Playlists, Artists oder Tracks bei Spotify.
              <br />
              Du kannst auch einen Spotify-Link oder eine ID einfügen.
            </div>
          ) : search.isLoading ? (
            <div className="flex items-center justify-center gap-2 px-3 py-6 text-[12px] text-muted-foreground">
              <Loader2 className="size-3.5 animate-spin" />
              Suche bei Spotify ...
            </div>
          ) : search.isError ? (
            <div className="px-3 py-6 text-center text-[12px] text-muted-foreground">
              Spotify-Suche nicht verfügbar.
            </div>
          ) : !hasResults ? (
            <div className="px-3 py-6 text-center text-[12px] text-muted-foreground">
              Keine Treffer.
            </div>
          ) : (
            <>
              {playlists.length > 0 && (
                <>
                  <SectionLabel label="Playlists" />
                  {playlists.map((playlist) => {
                    const attachment = playlistToAttachment(playlist);
                    return (
                      <ResultRow
                        key={`p-${playlist.id}`}
                        attachment={attachment}
                        isAttached={attachedKey.has(
                          `${attachment.kind}:${attachment.id}`,
                        )}
                        onPick={() => pick(attachment)}
                      />
                    );
                  })}
                </>
              )}
              {artists.length > 0 && (
                <>
                  <SectionLabel label="Artists" />
                  {artists.map((artist) => {
                    const attachment = artistToAttachment(artist);
                    return (
                      <ResultRow
                        key={`a-${artist.id}`}
                        attachment={attachment}
                        isAttached={attachedKey.has(
                          `${attachment.kind}:${attachment.id}`,
                        )}
                        onPick={() => pick(attachment)}
                      />
                    );
                  })}
                </>
              )}
              {tracks.length > 0 && (
                <>
                  <SectionLabel label="Tracks" />
                  {tracks.map((track) => {
                    const attachment = trackToAttachment(track);
                    return (
                      <ResultRow
                        key={`t-${track.id}`}
                        attachment={attachment}
                        isAttached={attachedKey.has(
                          `${attachment.kind}:${attachment.id}`,
                        )}
                        onPick={() => pick(attachment)}
                      />
                    );
                  })}
                </>
              )}
            </>
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
};
