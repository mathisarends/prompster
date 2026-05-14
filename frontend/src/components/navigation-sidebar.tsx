import { useEffect, useMemo, useRef, useState } from "react";
import { MessageCircle, PanelLeft, Plus, Search, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogClose, DialogContent } from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { mockChats, type ChatHistoryEntry } from "@/lib/mockChats";
import { PrompsterLogo } from "./prompster-logo";

type NavigationSidebarProps = {
  open: boolean;
  onToggle: () => void;
  onNewChat: () => void;
  onSelectChat: (chat: ChatHistoryEntry) => void;
  activeChatId?: string;
};

export const NavigationSidebar = ({
  open,
  onToggle,
  onNewChat,
  onSelectChat,
  activeChatId,
}: NavigationSidebarProps) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (searchOpen) {
      searchInputRef.current?.focus();
    }
  }, [searchOpen]);

  const visibleChats = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) {
      return mockChats;
    }
    return mockChats.filter((chat) => chat.title.toLowerCase().includes(query));
  }, [searchQuery]);

  const selectChat = (chat: ChatHistoryEntry) => {
    onSelectChat(chat);
    setSearchOpen(false);
  };

  return (
    <>
      <aside
        data-state={open ? "open" : "closed"}
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground transition-[width] duration-300 ease-out",
          open ? "w-72" : "w-14",
        )}
      >
        {open ? (
          <div className="flex items-center justify-between gap-2 px-3 py-3">
            <PrompsterLogo />
            <div className="flex items-center gap-1">
              <Button
                size="icon-sm"
                variant="ghost"
                onClick={onNewChat}
                aria-label="Neuen Chat starten"
                className="hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
              >
                <Plus className="size-4" />
              </Button>
              <Button
                size="icon-sm"
                variant="ghost"
                onClick={() => setSearchOpen(true)}
                aria-label="Suche oeffnen"
                className="hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
              >
                <Search className="size-4" />
              </Button>
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
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3 px-1 py-3">
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
              onClick={onNewChat}
              aria-label="Neuen Chat starten"
              className="rounded-full bg-sidebar-accent hover:bg-sidebar-accent/80 hover:text-sidebar-accent-foreground"
            >
              <Plus className="size-4" />
            </Button>
            <Button
              size="icon-sm"
              variant="ghost"
              onClick={() => setSearchOpen(true)}
              aria-label="Suche oeffnen"
              className="hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
            >
              <Search className="size-5" />
            </Button>
          </div>
        )}

        {open ? (
          <ScrollArea className="min-h-0 flex-1 px-2">
            <div className="pb-2 pt-1">
              <p className="px-2 pb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground/80">
                Verlauf
              </p>
              <ul className="space-y-0.5">
                {mockChats.map((chat) => {
                  const isActive = chat.id === activeChatId;
                  return (
                    <li key={chat.id}>
                      <button
                        type="button"
                        onClick={() => selectChat(chat)}
                        className={cn(
                          "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors",
                          isActive
                            ? "bg-sidebar-accent text-sidebar-accent-foreground"
                            : "text-sidebar-foreground/80 hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
                        )}
                      >
                        <MessageCircle className="size-4 shrink-0" />
                        <span className="truncate">{chat.title}</span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          </ScrollArea>
        ) : (
          <div className="flex-1" />
        )}

        <div className="border-t border-sidebar-border px-1 py-3">
          {open ? (
            <div className="flex items-center gap-2.5 px-2">
              <div className="grid size-9 place-items-center rounded-full bg-sidebar-accent text-xs font-semibold text-sidebar-accent-foreground">
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
              <div className="grid size-8 place-items-center rounded-full bg-sidebar-accent text-xs font-semibold text-sidebar-accent-foreground">
                MA
              </div>
            </div>
          )}
        </div>
      </aside>

      <Dialog open={searchOpen} onOpenChange={setSearchOpen}>
        <DialogContent className="top-10 max-h-[min(42rem,calc(100vh-5rem))] max-w-4xl overflow-hidden rounded-2xl border-white/15 bg-sidebar/95 p-0 shadow-2xl backdrop-blur-xl">
          <div className="flex items-center gap-3 border-b border-sidebar-border px-5 py-4">
            <Search className="size-5 shrink-0 text-muted-foreground" />
            <input
              ref={searchInputRef}
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
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

          <ScrollArea className="h-[min(32rem,calc(100vh-11rem))]">
            <div className="p-3">
              {visibleChats.length > 0 ? (
                <ul className="space-y-1">
                  {visibleChats.map((chat) => (
                    <li key={chat.id}>
                      <button
                        type="button"
                        onClick={() => selectChat(chat)}
                        className={cn(
                          "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors hover:bg-sidebar-accent/70",
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
                  Keine Chats fuer diese Suche.
                </p>
              )}
            </div>
          </ScrollArea>
        </DialogContent>
      </Dialog>
    </>
  );
};
