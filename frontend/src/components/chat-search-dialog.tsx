import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { MessageCircle, Search, X } from "lucide-react";

import { Dialog, DialogClose, DialogContent } from "@/components/ui/dialog";
import { useListKeyboardNavigation } from "@/hooks/useKeyboardShortcut";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { mockChats, type ChatHistoryEntry } from "@/lib/mockChats";

type ChatSearchDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelectChat: (chat: ChatHistoryEntry) => void;
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
  const searchInputRef = useRef<HTMLInputElement>(null);
  const itemRefs = useRef<Array<HTMLButtonElement | null>>([]);

  useEffect(() => {
    if (open) {
      requestAnimationFrame(() => searchInputRef.current?.focus());
    }
  }, [open]);

  const visibleChats = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return mockChats;
    return mockChats.filter((chat) => chat.title.toLowerCase().includes(query));
  }, [searchQuery]);

  const selectChat = (chat: ChatHistoryEntry) => {
    onSelectChat(chat);
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
  } = useListKeyboardNavigation<ChatHistoryEntry, HTMLInputElement>({
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
      <DialogContent className="top-20 max-h-[min(42rem,calc(100vh-7rem))] max-w-4xl overflow-hidden rounded-2xl border-white/15 bg-sidebar/95 p-0 shadow-2xl backdrop-blur-xl">
        <div className="flex items-center gap-3 border-b border-sidebar-border px-5 py-3">
          <Search className="size-5 shrink-0 text-muted-foreground" />
          <input
            ref={searchInputRef}
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            onKeyDown={handleSearchInputKeyDown}
            placeholder="Chats und Projekte durchsuchen"
            className="h-10 min-w-0 flex-1 bg-transparent text-base text-sidebar-foreground outline-none placeholder:text-muted-foreground"
          />
          <DialogClose
            aria-label="Suche schliessen"
            className="grid size-9 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
          >
            <X className="size-5" />
          </DialogClose>
        </div>

        <ScrollArea className="h-[min(32rem,calc(100vh-13rem))]">
          <div className="p-3">
            {visibleChats.length > 0 ? (
              <ul className="space-y-1">
                {visibleChats.map((chat, index) => (
                  <li key={chat.id}>
                    <button
                      ref={(element) => {
                        itemRefs.current[index] = element;
                      }}
                      type="button"
                      onClick={() => selectChat(chat)}
                      onMouseEnter={() => setHighlightedIndex(index)}
                      className={cn(
                        "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors hover:bg-sidebar-accent/70",
                        index === highlightedIndex &&
                          "bg-sidebar-accent/80 text-sidebar-accent-foreground",
                        chat.id === activeChatId &&
                          "bg-sidebar-accent text-sidebar-accent-foreground",
                      )}
                    >
                      <MessageCircle className="size-5 shrink-0 text-muted-foreground" />
                      <span className="min-w-0 flex-1 truncate text-base font-medium">
                        {chat.title}
                      </span>
                      <span className="shrink-0 text-sm text-muted-foreground">
                        {chat.group}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="px-3 py-8 text-center text-sm text-muted-foreground">
                Keine Chats für diese Suche.
              </p>
            )}
          </div>
        </ScrollArea>

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
