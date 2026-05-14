import { useEffect, useMemo, useRef, useState } from "react";
import { PanelLeft, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { mockChats, type ChatHistoryEntry } from "@/lib/mockChats";

type NavigationSidebarProps = {
  open: boolean;
  onToggle: () => void;
  onSelectChat: (chat: ChatHistoryEntry) => void;
  activeChatId?: string;
};

export const NavigationSidebar = ({
  open,
  onToggle,
  onSelectChat,
  activeChatId,
}: NavigationSidebarProps) => {
  const [searchQuery, setSearchQuery] = useState("");
  const shouldFocusSearchRef = useRef(false);
  const searchInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open && shouldFocusSearchRef.current) {
      searchInputRef.current?.focus();
      shouldFocusSearchRef.current = false;
    }
  }, [open]);

  const handleSearchIconClick = () => {
    if (!open) onToggle();
    shouldFocusSearchRef.current = true;
  };

  const visibleChats = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) {
      return mockChats;
    }
    return mockChats.filter((chat) => chat.title.toLowerCase().includes(query));
  }, [searchQuery]);

  return (
    <aside
      data-state={open ? "open" : "closed"}
      className={cn(
        "fixed inset-y-0 left-0 z-40 flex flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground transition-[width] duration-300 ease-out",
        open ? "w-72" : "w-16",
      )}
    >
      {open ? (
        <div className="flex items-center justify-between gap-2 px-3 py-3">
          <div className="flex items-center gap-3">
            <div className="grid size-9 place-items-center rounded-xl bg-sidebar-accent text-sidebar-accent-foreground text-lg font-bold">
              P
            </div>
            <div className="min-w-0">
              <p className="truncate text-base font-semibold tracking-tight">
                Prompster
              </p>
            </div>
          </div>
          <Button
            size="icon-sm"
            variant="ghost"
            onClick={onToggle}
            aria-label="Sidebar einklappen"
            className="hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
          >
            <PanelLeft className="size-4 transition-transform" />
          </Button>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-1 px-2 py-2">
          <Button
            size="icon-sm"
            variant="ghost"
            onClick={onToggle}
            aria-label="Sidebar ausklappen"
            className="hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
          >
            <PanelLeft className="size-4 rotate-180 transition-transform" />
          </Button>
          <Button
            size="icon-sm"
            variant="ghost"
            onClick={handleSearchIconClick}
            aria-label="Suche öffnen"
            className="hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
          >
            <Search className="size-4" />
          </Button>
        </div>
      )}

      <div className="space-y-2 px-3 pb-3">
        {open ? (
          <div className="relative">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              ref={searchInputRef}
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="Chats durchsuchen"
              className="h-9 border-sidebar-border/70 bg-sidebar-accent/35 pl-8 text-sm text-sidebar-foreground placeholder:text-muted-foreground"
            />
          </div>
        ) : (
          <div className="h-0" />
        )}
      </div>

      {open ? (
        <>
          <div className="px-3 pb-0">
            <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground/80">
              Verlauf
            </p>
          </div>

          <ScrollArea className="min-h-0 flex-1 px-2">
            <div className="pt-0.5 pb-2">
              {visibleChats.length > 0 ? (
                <ul className="space-y-0.5">
                  {visibleChats.map((chat) => {
                    const isActive = chat.id === activeChatId;
                    return (
                      <li key={chat.id}>
                        <button
                          type="button"
                          onClick={() => onSelectChat(chat)}
                          className={cn(
                            "w-full rounded-md px-2 py-1.5 text-left text-sm transition-colors",
                            isActive
                              ? "bg-sidebar-accent text-sidebar-accent-foreground"
                              : "text-sidebar-foreground/80 hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
                          )}
                        >
                          <span className="truncate">{chat.title}</span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <p className="px-2 py-3 text-sm text-muted-foreground">
                  Keine Chats fur diese Suche.
                </p>
              )}
            </div>
          </ScrollArea>
        </>
      ) : (
        <div className="flex-1" />
      )}

      <div className="border-t border-sidebar-border px-3 py-3">
        {open ? (
          <div className="flex items-center gap-2.5">
            <div className="grid size-9 place-items-center rounded-full bg-sidebar-accent text-sidebar-accent-foreground text-xs font-semibold">
              MA
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">Mathis Arends</p>
              <p className="truncate text-xs text-muted-foreground">
                Free Plan
              </p>
            </div>
          </div>
        ) : (
          <div className="grid place-items-center">
            <div className="grid size-9 place-items-center rounded-full bg-sidebar-accent text-sidebar-accent-foreground text-sm font-semibold">
              MA
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};
