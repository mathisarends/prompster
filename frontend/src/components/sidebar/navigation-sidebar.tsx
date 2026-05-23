import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useListSessions } from "@/api/generated/session-api";
import type { SessionSummaryResponse } from "@/api/generated/model";
import { spotifyDisconnect } from "@/api/generated/spotify/spotify";
import { getGetMeQueryKey, useGetMe } from "@/api/generated/user-api";
import { useAuth } from "@/auth/use-auth";

import { ChatSearchDialog } from "@/components/chat/chat-search-dialog";
import { type ShortcutKey } from "@/components/sidebar/keyboard-shortcut-hint";
import { NavigationSidebarSessions } from "@/components/sidebar/navigation-sidebar-sessions";
import { NavigationSidebarTop } from "@/components/sidebar/navigation-sidebar-top";
import { NavigationSidebarUserMenu } from "@/components/sidebar/navigation-sidebar-user-menu";
import { useKeyboardShortcut } from "@/hooks/useKeyboardShortcut";
import { useSpotifyOAuthPopup } from "@/hooks/useSpotifyOAuthPopup";
import { useSessionStarActions } from "@/hooks/useSessionStarActions";
import { toSessionHistoryEntries } from "@/components/sidebar/session-history-utils";
import {
  DeleteChatDialog,
  RenameChatDialog,
} from "@/components/sidebar/sidebar-session-dialogs";
import { cn } from "@/lib/utils";

const NEW_CHAT_SHORTCUT: ShortcutKey[] = ["mod", "shift", "o"];
const SEARCH_SHORTCUT: ShortcutKey[] = ["mod", "k"];
const TOGGLE_SIDEBAR_SHORTCUT: ShortcutKey[] = ["mod", "b"];

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
  const [renameTarget, setRenameTarget] =
    useState<SessionSummaryResponse | null>(null);
  const [deleteTarget, setDeleteTarget] =
    useState<SessionSummaryResponse | null>(null);
  const { isSpotifyOAuthLoading, openSpotifyOAuthPopup } =
    useSpotifyOAuthPopup();
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

  const handleSpotifyDisconnect = async () => {
    await spotifyDisconnect();
    void queryClient.invalidateQueries({ queryKey: getGetMeQueryKey() });
    toast.success("Spotify getrennt.");
  };

  useKeyboardShortcut({ ctrlOrMeta: true, key: "k" }, () => {
    setSearchOpen((previous) => !previous);
  });

  useKeyboardShortcut(
    { ctrlOrMeta: true, key: "b", ignoreInEditable: true },
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
        <NavigationSidebarTop
          open={open}
          onToggle={onToggle}
          onNewChat={onNewChat}
          onNewChatNewTab={onNewChatNewTab}
          onOpenSearch={() => setSearchOpen(true)}
          newChatShortcut={NEW_CHAT_SHORTCUT}
          searchShortcut={SEARCH_SHORTCUT}
          toggleSidebarShortcut={TOGGLE_SIDEBAR_SHORTCUT}
        />

        <NavigationSidebarSessions
          open={open}
          isLoadingSessions={isLoadingSessions}
          sessions={sessions}
          starredSessions={starredSessions}
          historySessions={historySessions}
          activeChatId={activeChatId}
          onSelectChat={selectChat}
          onToggleStar={toggleStar}
          onRenameChat={setRenameTarget}
          onDeleteChat={setDeleteTarget}
          isTogglingFor={isTogglingFor}
        />

        <NavigationSidebarUserMenu
          open={open}
          user={user}
          isSpotifyOAuthLoading={isSpotifyOAuthLoading}
          onSpotifyConnect={openSpotifyOAuthPopup}
          onSpotifyDisconnect={() => void handleSpotifyDisconnect()}
          onSignOut={() => void signOut()}
        />
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
