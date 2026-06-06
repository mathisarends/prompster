import {
  type KeyboardEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Paperclip, Search } from "lucide-react";

import { useSearchSpotify } from "@/api/generated/spotify/spotify";
import { SpotifySearchType } from "@/api/generated/model";
import { Button } from "@/shared/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/shared/ui/popover";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/shared/ui/tooltip";
import { useDebouncedValue } from "@/shared/hooks/useDebouncedValue";
import { useListKeyboardNavigation } from "@/shared/hooks/useKeyboardShortcut";
import { cn } from "@/shared/lib/utils";

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
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  query?: string;
  onQueryChange?: (query: string) => void;
  onTriggerClick?: () => void;
  hideSearchInput?: boolean;
  onPick?: () => void;
};

type AttachmentSuggestion =
  | { type: "parsed" }
  | { type: "attachment"; attachment: ChatAttachment };

const MIN_QUERY_LENGTH = 2;
const SEARCH_DEBOUNCE_MS = 180;

export const AttachmentPopover = ({
  attachments,
  onAdd,
  disabled,
  triggerClassName,
  onTriggerClick,
  open: controlledOpen,
  onOpenChange,
  query: controlledQuery,
  onQueryChange,
  hideSearchInput = false,
  onPick,
}: AttachmentPopoverProps) => {
  const [internalOpen, setInternalOpen] = useState(false);
  const [internalQuery, setInternalQuery] = useState("");
  const [resultFilter, setResultFilter] =
    useState<AttachmentResultFilter>("all");
  const inputRef = useRef<HTMLInputElement>(null);
  const itemRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const open = controlledOpen ?? internalOpen;
  const query = controlledQuery ?? internalQuery;
  const debouncedQuery = useDebouncedValue(query.trim(), SEARCH_DEBOUNCE_MS);

  const setQuery = useCallback(
    (nextQuery: string) => {
      if (controlledQuery === undefined) {
        setInternalQuery(nextQuery);
      }

      onQueryChange?.(nextQuery);
    },
    [controlledQuery, onQueryChange],
  );

  const handleOpenChange = (next: boolean) => {
    if (controlledOpen === undefined) {
      setInternalOpen(next);
    }

    onOpenChange?.(next);

    if (!next && controlledQuery === undefined) {
      setQuery("");
    }
  };

  useEffect(() => {
    if (!open || hideSearchInput) return;
    const id = window.setTimeout(() => inputRef.current?.focus(), 30);
    return () => window.clearTimeout(id);
  }, [hideSearchInput, open]);

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

  const playlists = useMemo(
    () => search.data?.playlists ?? [],
    [search.data?.playlists],
  );
  const artists = useMemo(
    () => search.data?.artists ?? [],
    [search.data?.artists],
  );
  const visiblePlaylists = useMemo(
    () => (resultFilter === "artists" ? [] : playlists),
    [playlists, resultFilter],
  );
  const visibleArtists = useMemo(
    () => (resultFilter === "playlists" ? [] : artists),
    [artists, resultFilter],
  );
  const hasResults = visiblePlaylists.length > 0 || visibleArtists.length > 0;

  const resultSuggestions = useMemo<AttachmentSuggestion[]>(() => {
    if (parsedRef) {
      return [{ type: "parsed" }];
    }

    return [
      ...visiblePlaylists.map((playlist) => ({
        type: "attachment" as const,
        attachment: playlistToAttachment(playlist),
      })),
      ...visibleArtists.map((artist) => ({
        type: "attachment" as const,
        attachment: artistToAttachment(artist),
      })),
    ];
  }, [parsedRef, visibleArtists, visiblePlaylists]);

  const pick = useCallback(
    (attachment: ChatAttachment) => {
      if (attachedKey.has(`${attachment.kind}:${attachment.id}`)) return;

      onAdd(attachment);
      setQuery("");
      onPick?.();

      if (!hideSearchInput) {
        inputRef.current?.focus();
      }
    },
    [attachedKey, hideSearchInput, onAdd, onPick, setQuery],
  );

  const addParsedRef = useCallback(() => {
    if (!parsedRef) return;

    pick({
      id: parsedRef.id,
      kind: parsedRef.kind,
      title: `Spotify ${parsedRef.kind.replace("spotify-", "")}`,
      subtitle: parsedRef.id,
      spotifyId: parsedRef.id,
    });
  }, [parsedRef, pick]);

  const confirmSuggestion = useCallback(
    (suggestion: AttachmentSuggestion) => {
      if (suggestion.type === "parsed") {
        addParsedRef();
        return;
      }

      pick(suggestion.attachment);
    },
    [addParsedRef, pick],
  );

  const {
    highlightedIndex,
    setHighlightedIndex,
    onKeyDown: handleListKeyDown,
  } = useListKeyboardNavigation<AttachmentSuggestion, HTMLInputElement>({
    items: resultSuggestions,
    open,
    onConfirm: confirmSuggestion,
    global: hideSearchInput,
    ignoreEditableGlobal: false,
  });

  useEffect(() => {
    if (highlightedIndex < 0) return;

    itemRefs.current[highlightedIndex]?.scrollIntoView({ block: "nearest" });
  }, [highlightedIndex]);

  const handlePopoverKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (!hideSearchInput) return;

    handleListKeyDown(event as unknown as KeyboardEvent<HTMLInputElement>);
  };

  const handleInputKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Escape") {
      event.preventDefault();
      handleOpenChange(false);
      return;
    }

    handleListKeyDown(event);
  };

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
                    size="icon"
                    disabled={disabled}
                    aria-label="Anhang hinzufügen oder @ eingeben"
                    className={cn(
                      "shrink-0 rounded-full text-muted-foreground hover:text-foreground",
                      triggerClassName,
                    )}
                    onClick={(event) => {
                      if (!onTriggerClick) return;

                      event.preventDefault();
                      onTriggerClick();
                    }}
                  >
                    <Paperclip className="size-4" />
                  </Button>
                }
              />
            }
          />
          <TooltipContent side="top" sideOffset={6} showArrow={false}>
            Anhang hinzufügen - Shortcut: @
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <PopoverContent
        side="top"
        align="start"
        sideOffset={10}
        className="w-80 p-0"
        onKeyDown={handlePopoverKeyDown}
      >
        {!hideSearchInput && (
          <div className="flex items-center gap-2 border-b border-white/[0.06] px-3 py-2.5">
            <Search className="size-4 shrink-0 text-muted-foreground" />
            <input
              ref={inputRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleInputKeyDown}
              placeholder="Spotify suchen oder Link einfügen"
              className="h-7 min-w-0 flex-1 bg-transparent text-[13px] outline-none placeholder:text-muted-foreground/70"
            />
          </div>
        )}

        <AttachmentSearchFilters
          value={resultFilter}
          onChange={setResultFilter}
        />

        <div className="prompster-scrollbar max-h-80 overflow-y-auto p-1.5">
          {parsedRef ? (
            <ParsedSpotifyAttachmentRow
              ref={(element) => {
                itemRefs.current[0] = element;
              }}
              parsedRef={parsedRef}
              onPick={addParsedRef}
              isHighlighted={highlightedIndex === 0}
              onMouseEnter={() => setHighlightedIndex(0)}
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
                  {visiblePlaylists.map((playlist, index) => {
                    const suggestion = resultSuggestions[index];
                    if (suggestion?.type !== "attachment") return null;

                    const { attachment } = suggestion;
                    return (
                      <AttachmentResultRow
                        key={`p-${playlist.id}`}
                        ref={(element) => {
                          itemRefs.current[index] = element;
                        }}
                        attachment={attachment}
                        isAttached={attachedKey.has(
                          `${attachment.kind}:${attachment.id}`,
                        )}
                        onPick={() => pick(attachment)}
                        isHighlighted={highlightedIndex === index}
                        onMouseEnter={() => setHighlightedIndex(index)}
                      />
                    );
                  })}
                </>
              )}
              {visibleArtists.length > 0 && (
                <>
                  <AttachmentSectionLabel label="Artists" />
                  {visibleArtists.map((artist, index) => {
                    const itemIndex = visiblePlaylists.length + index;
                    const suggestion = resultSuggestions[itemIndex];
                    if (suggestion?.type !== "attachment") return null;

                    const { attachment } = suggestion;
                    return (
                      <AttachmentResultRow
                        key={`a-${artist.id}`}
                        ref={(element) => {
                          itemRefs.current[itemIndex] = element;
                        }}
                        attachment={attachment}
                        isAttached={attachedKey.has(
                          `${attachment.kind}:${attachment.id}`,
                        )}
                        onPick={() => pick(attachment)}
                        isHighlighted={highlightedIndex === itemIndex}
                        onMouseEnter={() => setHighlightedIndex(itemIndex)}
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
