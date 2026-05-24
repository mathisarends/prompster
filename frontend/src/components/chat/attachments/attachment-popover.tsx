import { useEffect, useMemo, useRef, useState } from "react";
import { Paperclip, Search } from "lucide-react";

import { useSearchSpotify } from "@/api/generated/spotify/spotify";
import { SpotifySearchType } from "@/api/generated/model";
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
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { cn } from "@/lib/utils";

import { AttachmentResultRow } from "./attachment-result-row";
import { AttachmentSearchFilters } from "./attachment-search-filters";
import type { AttachmentResultFilter } from "./attachment-search-filters";
import { AttachmentSearchSkeleton } from "./attachment-search-skeleton";
import { AttachmentSectionLabel } from "./attachment-section-label";
import type { ChatAttachment } from "./attachment-types";
import { ParsedSpotifyAttachmentRow } from "./parsed-spotify-attachment-row";
import { parseSpotifyRef } from "./spotify-id-parser";
import {
  artistToAttachment,
  playlistToAttachment,
} from "./spotify-attachment-mappers";

type AttachmentPopoverProps = {
  attachments: ChatAttachment[];
  onAdd: (attachment: ChatAttachment) => void;
  disabled?: boolean;
  triggerClassName?: string;
};

const MIN_QUERY_LENGTH = 2;
const SEARCH_DEBOUNCE_MS = 180;

export const AttachmentPopover = ({
  attachments,
  onAdd,
  disabled,
  triggerClassName,
}: AttachmentPopoverProps) => {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [resultFilter, setResultFilter] =
    useState<AttachmentResultFilter>("all");
  const inputRef = useRef<HTMLInputElement>(null);
  const debouncedQuery = useDebouncedValue(query.trim(), SEARCH_DEBOUNCE_MS);

  const handleOpenChange = (next: boolean) => {
    setOpen(next);
    if (!next) {
      setQuery("");
    }
  };

  useEffect(() => {
    if (!open) return;
    const id = window.setTimeout(() => inputRef.current?.focus(), 30);
    return () => window.clearTimeout(id);
  }, [open]);

  const parsedRef = useMemo(() => {
    const ref = parseSpotifyRef(query);
    return ref?.kind === "spotify-track" ? null : ref;
  }, [query]);

  const canSearch = !parsedRef && debouncedQuery.length >= MIN_QUERY_LENGTH;

  const searchParams = useMemo(
    () => ({
      query: debouncedQuery || "_",
      limit: 6,
      types: [SpotifySearchType.playlist, SpotifySearchType.artist],
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
  const visiblePlaylists = resultFilter === "artists" ? [] : playlists;
  const visibleArtists = resultFilter === "playlists" ? [] : artists;
  const hasResults = visiblePlaylists.length > 0 || visibleArtists.length > 0;

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

        <AttachmentSearchFilters
          value={resultFilter}
          onChange={setResultFilter}
        />

        <div className="prompster-scrollbar max-h-80 overflow-y-auto p-1.5">
          {parsedRef ? (
            <ParsedSpotifyAttachmentRow
              parsedRef={parsedRef}
              onPick={addParsedRef}
            />
          ) : !canSearch ? (
            <div className="px-3 py-6 text-center text-[12px] text-muted-foreground">
              Suche nach Playlists oder Artists bei Spotify.
              <br />
              Du kannst auch einen Spotify-Link einfügen.
            </div>
          ) : search.isLoading ? (
            <AttachmentSearchSkeleton />
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
              {visiblePlaylists.length > 0 && (
                <>
                  <AttachmentSectionLabel label="Playlists" />
                  {visiblePlaylists.map((playlist) => {
                    const attachment = playlistToAttachment(playlist);
                    return (
                      <AttachmentResultRow
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
              {visibleArtists.length > 0 && (
                <>
                  <AttachmentSectionLabel label="Artists" />
                  {visibleArtists.map((artist) => {
                    const attachment = artistToAttachment(artist);
                    return (
                      <AttachmentResultRow
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
            </>
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
};
