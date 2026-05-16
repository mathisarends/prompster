import { useState } from "react";
import { LogOut, MessageCircle, PanelLeft, Plus, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ChatSearchDialog } from "@/components/chat-search-dialog";
import { useKeyboardShortcut } from "@/hooks/useKeyboardShortcut";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { mockChats, type ChatHistoryEntry } from "@/lib/mockChats";
import { PrompsterLogo } from "./prompster-logo";

type NavigationSidebarProps = {
  open: boolean;
  onToggle: () => void;
  onNewChat: () => void;
  onNewChatNewTab?: () => void;
  onSelectChat: (chat: ChatHistoryEntry) => void;
  onLogout?: () => void;
  activeChatId?: string;
};

export const NavigationSidebar = ({
  open,
  onToggle,
  onNewChat,
  onNewChatNewTab,
  onSelectChat,
  onLogout,
  activeChatId,
}: NavigationSidebarProps) => {
  const [searchOpen, setSearchOpen] = useState(false);

  useKeyboardShortcut({ ctrlOrMeta: true, key: "k" }, () => {
    setSearchOpen((previous) => !previous);
  });

  useKeyboardShortcut(
    { ctrlOrMeta: true, code: "Period", ignoreInEditable: true },
    () => {
      onToggle();
    },
  );

  useKeyboardShortcut({ ctrlOrMeta: true, shiftKey: true, key: "o" }, () => {
    onNewChat();
  });

  const selectChat = (chat: ChatHistoryEntry) => {
    onSelectChat(chat);
    setSearchOpen(false);
  };

  return (
    <>
      <aside
        data-state={open ? "open" : "closed"}
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground",
          "transition-[width,transform] duration-300 ease-out",
          open
            ? "w-72 translate-x-0"
            : "w-72 -translate-x-full sm:w-14 sm:translate-x-0",
        )}
      >
        {open ? (
          <div className="space-y-4 px-3 py-3">
            <div className="flex items-center justify-between gap-2">
              <PrompsterLogo />
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

            <div className="space-y-1">
              <button
                type="button"
                onClick={(e) => {
                  if ((e.ctrlKey || e.metaKey) && onNewChatNewTab) {
                    e.preventDefault();
                    onNewChatNewTab();
                  } else {
                    onNewChat();
                  }
                }}
                className="flex h-10 w-full items-center gap-3 rounded-md px-2 text-left text-sm font-medium text-sidebar-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
              >
                <Plus className="size-5 shrink-0" />
                <span>Neuer Chat</span>
              </button>
              <button
                type="button"
                onClick={() => setSearchOpen(true)}
                className="flex h-10 w-full items-center gap-3 rounded-md px-2 text-left text-sm font-medium text-sidebar-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
              >
                <Search className="size-5 shrink-0" />
                <span>Suchen</span>
              </button>
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
              onClick={(e) => {
                if ((e.ctrlKey || e.metaKey) && onNewChatNewTab) {
                  e.preventDefault();
                  onNewChatNewTab();
                } else {
                  onNewChat();
                }
              }}
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
          <DropdownMenu>
            {open ? (
              <DropdownMenuTrigger
                aria-label="Profilmenue oeffnen"
                className="flex h-12 w-full items-center gap-2.5 rounded-md px-2 text-left transition-colors hover:bg-sidebar-accent focus-visible:ring-2 focus-visible:ring-sidebar-ring"
              >
                <Avatar className="bg-sidebar-accent" size="default">
                  <AvatarFallback className="bg-sidebar-accent text-xs font-semibold text-sidebar-accent-foreground">
                    MA
                  </AvatarFallback>
                </Avatar>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">Mathis Arends</p>
                  <p className="truncate text-xs text-muted-foreground">
                    Free Plan
                  </p>
                </div>
              </DropdownMenuTrigger>
            ) : (
              <div className="grid place-items-center">
                <DropdownMenuTrigger
                  aria-label="Profilmenue oeffnen"
                  className="grid size-9 place-items-center rounded-md transition-colors hover:bg-sidebar-accent focus-visible:ring-2 focus-visible:ring-sidebar-ring"
                >
                  <Avatar className="bg-sidebar-accent" size="default">
                    <AvatarFallback className="bg-sidebar-accent text-xs font-semibold text-sidebar-accent-foreground">
                      MA
                    </AvatarFallback>
                  </Avatar>
                </DropdownMenuTrigger>
              </div>
            )}
            <DropdownMenuContent
              align={open ? "start" : "center"}
              side="top"
              sideOffset={8}
            >
              <DropdownMenuItem onClick={onLogout}>
                <LogOut />
                <span>Abmelden</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </aside>

      <ChatSearchDialog
        open={searchOpen}
        onOpenChange={setSearchOpen}
        onSelectChat={onSelectChat}
        activeChatId={activeChatId}
      />
    </>
  );
};
