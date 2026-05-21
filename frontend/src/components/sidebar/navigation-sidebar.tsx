import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ChevronsUpDown,
  LogOut,
  Music2,
  PanelLeft,
  Plus,
  Search,
} from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useListSessions } from "@/api/generated/session-api";
import type { SessionSummaryResponse } from "@/api/generated/model";
import {
  getSpotifyConnectQueryKey,
  spotifyDisconnect,
} from "@/api/generated/spotify/spotify";
import { getGetMeQueryKey, useGetMe } from "@/api/generated/user-api";
import { AXIOS_INSTANCE } from "@/api/http-client";
import { useAuth } from "@/auth/use-auth";

import { Button } from "@/components/ui/button";
import { ChatSearchDialog } from "@/components/chat/chat-search-dialog";
import {
  KeyboardShortcutHint,
  formatShortcutKey,
  type ShortcutKey,
} from "@/components/sidebar/keyboard-shortcut-hint";
import { useKeyboardShortcut } from "@/hooks/useKeyboardShortcut";
import { useSessionStarActions } from "@/hooks/useSessionStarActions";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ScrollArea } from "@/components/ui/scroll-area";
import { toSessionHistoryEntries } from "@/components/sidebar/session-history-utils";
import { SidebarSessionItem } from "@/components/sidebar/sidebar-session-item";
import {
  DeleteChatDialog,
  RenameChatDialog,
} from "@/components/sidebar/sidebar-session-dialogs";
import { PrompsterLogo } from "@/components/prompster-logo";
import { cn } from "@/lib/utils";

const NEW_CHAT_SHORTCUT: ShortcutKey[] = ["mod", "shift", "o"];
const SEARCH_SHORTCUT: ShortcutKey[] = ["mod", "k"];
const TOGGLE_SIDEBAR_SHORTCUT: ShortcutKey[] = ["mod", "shift", "."];
const SPOTIFY_OAUTH_MESSAGE_TYPE = "prompster-spotify-oauth";

type SpotifyOAuthPopupMessage = {
  type: typeof SPOTIFY_OAUTH_MESSAGE_TYPE;
  status: "success" | "error";
  reason?: string;
};

const isSpotifyOAuthPopupMessage = (
  data: unknown,
): data is SpotifyOAuthPopupMessage => {
  if (typeof data !== "object" || data === null) return false;

  const candidate = data as { type?: unknown; status?: unknown };
  return (
    candidate.type === SPOTIFY_OAUTH_MESSAGE_TYPE &&
    (candidate.status === "success" || candidate.status === "error")
  );
};

const resolveBackendOrigin = (): string => {
  const baseUrl =
    AXIOS_INSTANCE.defaults.baseURL ??
    `${window.location.protocol}//${window.location.hostname}:8000`;

  return new URL(baseUrl, window.location.origin).origin;
};

const getSpotifyConnectUrl = (): string => {
  const [spotifyConnectPath] = getSpotifyConnectQueryKey();
  return new URL(spotifyConnectPath, resolveBackendOrigin()).toString();
};

const InlineShortcutKeys = ({ keys }: { keys: ShortcutKey[] }) => (
  <span className="ml-auto flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
    {keys.map((key, index) => (
      <kbd
        key={`${key}-${index}`}
        className="min-w-5 rounded border border-sidebar-border/60 bg-sidebar px-1.5 py-0.5 text-center text-[10px] font-semibold leading-none text-sidebar-foreground/80"
      >
        {formatShortcutKey(key)}
      </kbd>
    ))}
  </span>
);

type NavigationSidebarProps = {
  open: boolean;
  onToggle: () => void;
  onNewChat: () => void;
  onNewChatNewTab?: () => void;
  onSelectChat: (session: SessionSummaryResponse) => void;
  activeChatId?: string;
};

export const NavigationSidebar = ({
  open,
  onToggle,
  onNewChat,
  onNewChatNewTab,
  onSelectChat,
  activeChatId,
}: NavigationSidebarProps) => {
  const { signOut } = useAuth();
  const queryClient = useQueryClient();
  const [searchOpen, setSearchOpen] = useState(false);
  const [isSpotifyOAuthLoading, setIsSpotifyOAuthLoading] = useState(false);
  const [renameTarget, setRenameTarget] =
    useState<SessionSummaryResponse | null>(null);
  const [deleteTarget, setDeleteTarget] =
    useState<SessionSummaryResponse | null>(null);
  const spotifyOAuthPopupRef = useRef<Window | null>(null);
  const spotifyPopupClosedCheckRef = useRef<number | null>(null);
  const { data: user } = useGetMe();
  const { data: sessionsData, isLoading: isLoadingSessions } = useListSessions({
    limit: 200,
    offset: 0,
  });

  const sessions = useMemo(
    () => toSessionHistoryEntries(sessionsData?.items ?? []),
    [sessionsData?.items],
  );
  const { starredSessions, historySessions } = useMemo(
    () => ({
      starredSessions: sessions.filter((session) => session.isStarred),
      historySessions: sessions.filter((session) => !session.isStarred),
    }),
    [sessions],
  );

  const { toggleStar, isTogglingFor } = useSessionStarActions();

  const stopSpotifyPopupClosedCheck = useCallback(() => {
    if (spotifyPopupClosedCheckRef.current !== null) {
      window.clearInterval(spotifyPopupClosedCheckRef.current);
      spotifyPopupClosedCheckRef.current = null;
    }
  }, []);

  useEffect(() => {
    const backendOrigin = resolveBackendOrigin();

    const handleMessage = (event: MessageEvent) => {
      if (event.origin !== backendOrigin) return;
      if (!isSpotifyOAuthPopupMessage(event.data)) return;

      stopSpotifyPopupClosedCheck();
      spotifyOAuthPopupRef.current?.close();
      spotifyOAuthPopupRef.current = null;
      setIsSpotifyOAuthLoading(false);

      if (event.data.status === "success") {
        void queryClient.invalidateQueries({ queryKey: getGetMeQueryKey() });
        toast.success("Spotify verbunden.");
      } else {
        toast.error(
          event.data.reason === "access_denied"
            ? "Spotify-Verbindung abgebrochen."
            : "Spotify-Verbindung fehlgeschlagen.",
        );
      }
    };

    window.addEventListener("message", handleMessage);
    return () => {
      window.removeEventListener("message", handleMessage);
      stopSpotifyPopupClosedCheck();
    };
  }, [queryClient, stopSpotifyPopupClosedCheck]);

  const handleSpotifyConnect = () => {
    if (isSpotifyOAuthLoading) return;

    const spotifyConnectUrl = getSpotifyConnectUrl();
    const oauthPopup = window.open(
      spotifyConnectUrl,
      SPOTIFY_OAUTH_MESSAGE_TYPE,
      "popup,width=520,height=720",
    );

    if (!oauthPopup) {
      window.location.assign(spotifyConnectUrl);
      return;
    }

    spotifyOAuthPopupRef.current = oauthPopup;
    setIsSpotifyOAuthLoading(true);

    stopSpotifyPopupClosedCheck();
    spotifyPopupClosedCheckRef.current = window.setInterval(() => {
      if (spotifyOAuthPopupRef.current?.closed) {
        stopSpotifyPopupClosedCheck();
        spotifyOAuthPopupRef.current = null;
        setIsSpotifyOAuthLoading(false);
      }
    }, 500);
  };

  const handleSpotifyDisconnect = async () => {
    await spotifyDisconnect();
    void queryClient.invalidateQueries({ queryKey: getGetMeQueryKey() });
    toast.success("Spotify getrennt.");
  };

  const initials =
    user?.name
      .split(" ")
      .map((part) => part[0])
      .join("")
      .toUpperCase()
      .slice(0, 2) ?? "";

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

  const selectChat = (session: SessionSummaryResponse) => {
    onSelectChat(session);
    setSearchOpen(false);
  };

  const handleSessionDeleted = (sessionId: string) => {
    if (sessionId === activeChatId) {
      onNewChat();
    }
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
              <KeyboardShortcutHint
                label="Sidebar einklappen"
                keys={TOGGLE_SIDEBAR_SHORTCUT}
              >
                <Button
                  size="icon-sm"
                  variant="ghost"
                  onClick={onToggle}
                  aria-label="Sidebar einklappen"
                  className="hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                >
                  <PanelLeft className="size-4 transition-transform" />
                </Button>
              </KeyboardShortcutHint>
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
                className="group flex h-10 w-full items-center gap-3 rounded-md px-2 text-left text-sm font-medium text-sidebar-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
              >
                <Plus className="size-5 shrink-0" />
                <span>Neuer Chat</span>
                <InlineShortcutKeys keys={NEW_CHAT_SHORTCUT} />
              </button>
              <button
                type="button"
                onClick={() => setSearchOpen(true)}
                className="group flex h-10 w-full items-center gap-3 rounded-md px-2 text-left text-sm font-medium text-sidebar-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
              >
                <Search className="size-5 shrink-0" />
                <span>Suchen</span>
                <InlineShortcutKeys keys={SEARCH_SHORTCUT} />
              </button>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3 px-1 py-3">
            <KeyboardShortcutHint
              label="Sidebar ausklappen"
              keys={TOGGLE_SIDEBAR_SHORTCUT}
            >
              <Button
                size="icon-sm"
                variant="ghost"
                onClick={onToggle}
                aria-label="Sidebar ausklappen"
                className="hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
              >
                <PanelLeft className="size-4 rotate-180 transition-transform" />
              </Button>
            </KeyboardShortcutHint>
            <KeyboardShortcutHint label="Neuer Chat" keys={NEW_CHAT_SHORTCUT}>
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
            </KeyboardShortcutHint>
            <KeyboardShortcutHint label="Suchen" keys={SEARCH_SHORTCUT}>
              <Button
                size="icon-sm"
                variant="ghost"
                onClick={() => setSearchOpen(true)}
                aria-label="Suche oeffnen"
                className="hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
              >
                <Search className="size-5" />
              </Button>
            </KeyboardShortcutHint>
          </div>
        )}

        {open ? (
          <ScrollArea className="min-h-0 flex-1 px-2">
            <div className="pb-2 pt-1">
              {isLoadingSessions ? (
                <p className="px-2 py-3 text-xs text-muted-foreground">
                  Lade Verlauf...
                </p>
              ) : sessions.length === 0 ? (
                <p className="px-2 py-3 text-xs text-muted-foreground">
                  Noch keine Sessions vorhanden.
                </p>
              ) : (
                <>
                  {starredSessions.length > 0 ? (
                    <div>
                      <p className="px-2 pb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground/80">
                        Markiert
                      </p>
                      <ul className="space-y-0.5 pb-3">
                        {starredSessions.map((session) => (
                          <SidebarSessionItem
                            key={session.id}
                            session={session}
                            isActive={session.id === activeChatId}
                            onSelect={() => selectChat(session)}
                            onToggleStar={() => toggleStar(session)}
                            onRename={() => setRenameTarget(session)}
                            onDelete={() => setDeleteTarget(session)}
                            isTogglingStar={isTogglingFor(session.id)}
                          />
                        ))}
                      </ul>
                    </div>
                  ) : null}

                  <div>
                    <p className="px-2 pb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground/80">
                      Verlauf
                    </p>
                    {historySessions.length === 0 ? (
                      <p className="px-2 py-3 text-xs text-muted-foreground">
                        Keine weiteren Sessions im Verlauf.
                      </p>
                    ) : (
                      <ul className="space-y-0.5">
                        {historySessions.map((session) => (
                          <SidebarSessionItem
                            key={session.id}
                            session={session}
                            isActive={session.id === activeChatId}
                            onSelect={() => selectChat(session)}
                            onToggleStar={() => toggleStar(session)}
                            onRename={() => setRenameTarget(session)}
                            onDelete={() => setDeleteTarget(session)}
                            isTogglingStar={isTogglingFor(session.id)}
                          />
                        ))}
                      </ul>
                    )}
                  </div>
                </>
              )}
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
                className="flex h-12 w-full cursor-pointer items-center gap-2.5 rounded-md border border-transparent px-2 text-left transition-colors hover:border-sidebar-border/80 hover:bg-sidebar-accent focus-visible:ring-2 focus-visible:ring-sidebar-ring data-[state=open]:border-sidebar-border/80 data-[state=open]:bg-sidebar-accent"
              >
                <Avatar className="bg-sidebar-accent" size="default">
                  <AvatarFallback className="bg-sidebar-accent text-xs font-semibold text-sidebar-accent-foreground">
                    {initials}
                  </AvatarFallback>
                </Avatar>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">
                    {user?.name ?? "Konto"}
                  </p>
                </div>
                <ChevronsUpDown className="size-4 shrink-0 text-sidebar-foreground/70" />
              </DropdownMenuTrigger>
            ) : (
              <div className="grid place-items-center">
                <DropdownMenuTrigger
                  aria-label="Profilmenue oeffnen"
                  className="grid size-9 cursor-pointer place-items-center rounded-md border border-transparent transition-colors hover:border-sidebar-border/80 hover:bg-sidebar-accent focus-visible:ring-2 focus-visible:ring-sidebar-ring data-[state=open]:border-sidebar-border/80 data-[state=open]:bg-sidebar-accent"
                >
                  <Avatar className="bg-sidebar-accent" size="default">
                    <AvatarFallback className="bg-sidebar-accent text-xs font-semibold text-sidebar-accent-foreground">
                      {initials}
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
              {user?.spotifyConnected ? (
                <DropdownMenuItem
                  onClick={() => void handleSpotifyDisconnect()}
                >
                  <Music2 />
                  <span>Spotify trennen</span>
                </DropdownMenuItem>
              ) : (
                <DropdownMenuItem
                  onClick={handleSpotifyConnect}
                  disabled={isSpotifyOAuthLoading}
                >
                  <Music2 />
                  <span>
                    {isSpotifyOAuthLoading
                      ? "Spotify verbindet..."
                      : "Spotify verbinden"}
                  </span>
                </DropdownMenuItem>
              )}
              <DropdownMenuItem onClick={() => void signOut()}>
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

      <RenameChatDialog
        session={renameTarget}
        open={renameTarget !== null}
        onOpenChange={(open) => {
          if (!open) setRenameTarget(null);
        }}
      />

      <DeleteChatDialog
        session={deleteTarget}
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
        onDeleted={handleSessionDeleted}
      />
    </>
  );
};
