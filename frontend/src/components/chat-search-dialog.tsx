import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { MessageCircle, Search, X } from "lucide-react";
import { useListSessions } from "@/api/generated/session-api";
import type { SessionSummaryResponse } from "@/api/generated/model";

import { Dialog, DialogClose, DialogContent } from "@/components/ui/dialog";
import { useListKeyboardNavigation } from "@/hooks/useKeyboardShortcut";
import {
  formatSessionTimestamp,
  toSessionHistoryEntries,
  type SessionHistoryEntry,
} from "@/components/session-history-utils";
import { cn } from "@/lib/utils";

type ChatSearchDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelectChat: (session: SessionSummaryResponse) => void;
  activeChatId?: string;
};

const ShortcutKey = ({ label }: { label: string }) => (
  <kbd className="min-w-5 rounded border border-sidebar-border bg-sidebar-accent px-1.5 py-0.5 text-center text-[10px] font-semibold leading-none text-sidebar-accent-foreground">
    {label}
  </kbd>
);

export const ChatSearchDialog = ({
  open,
  onOpenChange,
  onSelectChat,
  activeChatId,
}: ChatSearchDialogProps) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const searchInputRef = useRef<HTMLInputElement>(null);
  const itemRefs = useRef<Array<HTMLButtonElement | null>>([]);

  useEffect(() => {
    if (open) {
      requestAnimationFrame(() => searchInputRef.current?.focus());
    }
  }, [open]);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      setDebouncedQuery(searchQuery.trim());
    }, 180);

    return () => {
      window.clearTimeout(timeout);
    };
  }, [searchQuery]);

  const { data: sessionsData, isFetching: isFetchingSessions } =
    useListSessions(
      {
        q: debouncedQuery.length > 0 ? debouncedQuery : null,
        limit: 50,
        offset: 0,
      },
      {
        query: {
          enabled: open,
        },
      },
    );

  const isSearching = debouncedQuery.length > 0;

  const { data: allSessionsData, isFetching: isFetchingAllSessions } =
    useListSessions(
      {
        q: null,
        limit: 1,
        offset: 0,
      },
      {
        query: {
          enabled: open && isSearching,
        },
      },
    );

  const visibleChats = useMemo(() => {
    return toSessionHistoryEntries(sessionsData?.items ?? []);
  }, [sessionsData?.items]);

  const hasAnySessions = isSearching
    ? (allSessionsData?.items.length ?? 0) > 0
    : visibleChats.length > 0;

  const isLoadingEmptyState =
    isFetchingSessions || (isSearching && isFetchingAllSessions);

  const selectChat = (session: SessionSummaryResponse) => {
    onSelectChat(session);
    onOpenChange(false);
  };

  const getInitialHighlightIndex = useCallback(() => {
    if (!activeChatId) {
      return 0;
    }

    return visibleChats.findIndex((chat) => chat.id === activeChatId);
  }, [activeChatId, visibleChats]);

  const {
    highlightedIndex,
    setHighlightedIndex,
    onKeyDown: handleSearchInputKeyDown,
  } = useListKeyboardNavigation<SessionHistoryEntry, HTMLInputElement>({
    items: visibleChats,
    open,
    onConfirm: selectChat,
    getInitialIndex: getInitialHighlightIndex,
  });

  useEffect(() => {
    if (highlightedIndex < 0) {
      return;
    }
    itemRefs.current[highlightedIndex]?.scrollIntoView({ block: "nearest" });
  }, [highlightedIndex]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="top-20 flex max-h-[min(42rem,calc(100vh-7rem))] max-w-4xl flex-col overflow-hidden rounded-2xl border-white/15 bg-sidebar/95 p-0 shadow-2xl backdrop-blur-xl">
        <div className="flex items-center gap-3 border-b border-sidebar-border px-5 py-3">
          <Search className="size-5 shrink-0 text-muted-foreground" />
          <input
            ref={searchInputRef}
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            onKeyDown={handleSearchInputKeyDown}
            placeholder="Chats durchsuchen"
            className="h-10 min-w-0 flex-1 bg-transparent text-base text-sidebar-foreground outline-none placeholder:text-muted-foreground"
          />
          <DialogClose
            aria-label="Suche schliessen"
            className="grid size-9 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
          >
            <X className="size-5" />
          </DialogClose>
        </div>

        <div className="max-h-[min(32rem,calc(100vh-13rem))] overflow-y-auto p-3">
          {visibleChats.length > 0 ? (
            <ul className="space-y-1">
              {visibleChats.map((session, index) => (
                <li key={session.id}>
                  <button
                    ref={(element) => {
                      itemRefs.current[index] = element;
                    }}
                    type="button"
                    onClick={() => selectChat(session)}
                    onMouseEnter={() => setHighlightedIndex(index)}
                    className={cn(
                      "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors hover:bg-sidebar-accent/70",
                      index === highlightedIndex &&
                        "bg-sidebar-accent/80 text-sidebar-accent-foreground",
                      session.id === activeChatId &&
                        "bg-sidebar-accent text-sidebar-accent-foreground",
                    )}
                  >
                    <MessageCircle className="size-5 shrink-0 text-muted-foreground" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-base font-medium">
                        {session.title}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {session.group}
                      </p>
                    </div>
                    <span className="shrink-0 text-sm text-muted-foreground">
                      {formatSessionTimestamp(session.last_activity_at)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <div className="rounded-lg px-2 py-4 text-left text-sm text-muted-foreground">
              <div>
                <p className="font-medium text-sidebar-foreground">
                  {isLoadingEmptyState
                    ? "Suche läuft..."
                    : hasAnySessions
                      ? "Keine Sessions für diese Suche."
                      : "Du hast noch keine Sessions."}
                </p>
                {!isLoadingEmptyState && !hasAnySessions ? (
                  <p className="mt-1">
                    Starte deinen ersten Chat, dann erscheinen deine Sessions
                    hier.
                  </p>
                ) : null}
              </div>
            </div>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-sidebar-border px-5 py-3 text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <span>Auswählen</span>
            <span className="flex items-center gap-1">
              <ShortcutKey label="ArrowUp" />
              <ShortcutKey label="ArrowDown" />
            </span>
          </div>

          <div className="flex items-center gap-2">
            <span>Öffnen</span>
            <ShortcutKey label="Enter" />
          </div>

          <div className="flex items-center gap-2">
            <span>Menü öffnen</span>
            <span className="flex items-center gap-1">
              <ShortcutKey label="Ctrl" />
              <ShortcutKey label="K" />
            </span>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
