import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigationType, useParams } from "react-router-dom";

import type {
  SessionResponse,
  UserCurationEventResponse,
} from "@/api/generated/model";
import { ChatSessionPane } from "@/components/chat/chat-session-pane";
import { DeckWorkspaceView } from "@/components/deck/deck-workspace-view";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { useLocalStorage } from "@/hooks/useLocalStorage";

import { useChatSession } from "./chat-page.hook";

type UserCurationTrackPlaybackState = {
  activeTrackUri: string | null;
  canControlPlayback: boolean;
  isPlaying: boolean;
};

type UserCurationTrackPlayerBridge = {
  activeTrackUri: string | null;
  isPlaying: boolean;
  onTogglePlayback: (event: UserCurationEventResponse) => void;
} | null;

type ChatRouteState = {
  session?: SessionResponse;
  streamInitialResponse?: boolean;
  initialPrompt?: string;
};

export const ChatPage = () => {
  const { chatId } = useParams();
  const sessionId = chatId ?? "";
  const location = useLocation();
  const navigationType = useNavigationType();
  const routeState = location.state as ChatRouteState | null;

  const initialSession = useMemo(() => {
    if (routeState?.session?.id !== sessionId) return undefined;
    return routeState.session;
  }, [routeState?.session, sessionId]);

  const {
    session,
    title,
    entries,
    playlist,
    isTitlePending,
    isStreaming,
    isStopping,
    isLoadingSession,
    isError,
    sendMessage,
    stopMessage,
    removePlaylistTrack,
  } = useChatSession({
    sessionId,
    initialSession,
    streamInitialResponse: Boolean(
      routeState?.streamInitialResponse && navigationType === "PUSH",
    ),
    initialPrompt: routeState?.initialPrompt,
  });

  const [workspaceLayout, setWorkspaceLayout] = useLocalStorage(
    "prompster.chat.workspace-layout",
    [62, 38],
  );
  const [canShowWorkspace, setCanShowWorkspace] = useState(() =>
    typeof window === "undefined"
      ? true
      : window.matchMedia("(min-width: 1024px)").matches,
  );
  const userCurationTrackPlayerRef = useRef<
    ((event: UserCurationEventResponse) => void) | null
  >(null);
  const [userCurationPlaybackState, setUserCurationPlaybackState] =
    useState<UserCurationTrackPlaybackState>({
      activeTrackUri: null,
      canControlPlayback: false,
      isPlaying: false,
    });
  useEffect(() => {
    const mediaQuery = window.matchMedia("(min-width: 1024px)");
    const handleChange = (event: MediaQueryListEvent) => {
      setCanShowWorkspace(event.matches);
    };

    mediaQuery.addEventListener("change", handleChange);
    return () => mediaQuery.removeEventListener("change", handleChange);
  }, []);

  const updateUserCurationTrackPlayer = useCallback(
    (bridge: UserCurationTrackPlayerBridge) => {
      userCurationTrackPlayerRef.current = bridge?.onTogglePlayback ?? null;
      setUserCurationPlaybackState({
        activeTrackUri: bridge?.activeTrackUri ?? null,
        canControlPlayback: Boolean(bridge),
        isPlaying: bridge?.isPlaying ?? false,
      });
    },
    [],
  );

  const toggleUserCurationEventTrackPlayback = useCallback(
    (event: UserCurationEventResponse) => {
      userCurationTrackPlayerRef.current?.(event);
    },
    [],
  );

  return (
    <div className="chat-page-background h-dvh overflow-hidden text-foreground">
      {playlist && canShowWorkspace ? (
        <ResizablePanelGroup
          orientation="horizontal"
          className="relative z-10 h-full"
          defaultLayout={{
            chat: workspaceLayout[0] ?? 62,
            workspace: workspaceLayout[1] ?? 38,
          }}
          onLayoutChanged={(layout) =>
            setWorkspaceLayout([layout.chat ?? 62, layout.workspace ?? 38])
          }
        >
          <ResizablePanel
            id="chat"
            defaultSize={workspaceLayout[0] ?? 62}
            minSize="30%"
          >
            <ChatSessionPane
              sessionId={sessionId}
              session={session}
              title={title}
              entries={entries}
              isTitlePending={isTitlePending}
              isStreaming={isStreaming}
              isStopping={isStopping}
              isLoadingSession={isLoadingSession}
              isError={isError}
              sendMessage={sendMessage}
              stopMessage={stopMessage}
              userCurationPlaybackState={userCurationPlaybackState}
              onToggleUserCurationTrackPlayback={
                toggleUserCurationEventTrackPlayback
              }
            />
          </ResizablePanel>
          <ResizableHandle withHandle className="bg-white/[0.06]" />
          <ResizablePanel
            id="workspace"
            defaultSize={workspaceLayout[1] ?? 38}
            minSize="20%"
            maxSize="70%"
            className="border-l border-white/[0.06]"
          >
            <DeckWorkspaceView
              sessionId={sessionId}
              playlist={playlist}
              onRemoveTrack={removePlaylistTrack}
              onCurationTrackPlayerChange={updateUserCurationTrackPlayer}
            />
          </ResizablePanel>
        </ResizablePanelGroup>
      ) : (
        <div className="relative z-10 flex h-full">
          <ChatSessionPane
            sessionId={sessionId}
            session={session}
            title={title}
            entries={entries}
            isTitlePending={isTitlePending}
            isStreaming={isStreaming}
            isStopping={isStopping}
            isLoadingSession={isLoadingSession}
            isError={isError}
            sendMessage={sendMessage}
            stopMessage={stopMessage}
            userCurationPlaybackState={userCurationPlaybackState}
            onToggleUserCurationTrackPlayback={
              toggleUserCurationEventTrackPlayback
            }
          />
        </div>
      )}
    </div>
  );
};
