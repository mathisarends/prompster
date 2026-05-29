import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import {
  useLocation,
  useNavigate,
  useNavigationType,
  useParams,
} from "react-router-dom";

import type {
  SessionResponse,
  UserCurationEventResponse,
} from "@/api/generated/model";
import { AssistantChatMessage } from "@/components/chat/assistant-chat-message";
import { ChatInputBox } from "@/components/chat/chat-input-box";
import { ChatMessageSkeleton } from "@/components/chat/chat-message-skeleton";
import { ChatPageHeader } from "@/components/chat/chat-page-header";
import { ChatThinkingIndicator } from "@/components/chat/chat-thinking-indicator";
import { DeckWorkspaceView } from "@/components/deck/deck-workspace-view";
import { FollowUpQuestionGroup } from "@/components/chat/follow-up-questions";
import { ToolCallAccordion } from "@/components/chat/tool-call-sequence";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { ScrollArea } from "@/components/ui/scroll-area";
import { UserChatMessage } from "@/components/chat/user-chat-message";
import { UserCurationEventContext } from "@/components/chat/user-curation";
import { useLocalStorage } from "@/hooks/useLocalStorage";
import { useStickyScroll } from "@/hooks/useStickyScroll";
import { cn } from "@/lib/utils";

import {
  getPendingFollowUpQuestion,
  toToolCallItems,
  type ChatEntry,
} from "./chat-page.state";
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

const shouldShowThinkingPlaceholder = (
  entries: ChatEntry[],
  isStreaming: boolean,
) => {
  if (!isStreaming) return false;

  const lastEntry = entries[entries.length - 1];
  if (!lastEntry) return true;
  if (lastEntry.kind === "assistant_message") return !lastEntry.isStreaming;
  if (lastEntry.kind === "tool_call_group") {
    return lastEntry.calls.every((call) => call.state !== "pending");
  }
  return true;
};

type ChatRouteState = {
  session?: SessionResponse;
  streamInitialResponse?: boolean;
  initialPrompt?: string;
};

export const ChatPage = () => {
  const { chatId } = useParams();
  const sessionId = chatId ?? "";
  const location = useLocation();
  const navigate = useNavigate();
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
    followUpDrafts,
    isTitlePending,
    isStreaming,
    isStopping,
    isLoadingSession,
    isError,
    sendMessage,
    stopMessage,
    answerFollowUp,
    skipFollowUps,
    updateFollowUpDraft,
    removePlaylistTrack,
  } = useChatSession({
    sessionId,
    initialSession,
    streamInitialResponse: Boolean(
      routeState?.streamInitialResponse && navigationType === "PUSH",
    ),
    initialPrompt: routeState?.initialPrompt,
  });

  const [prompt, setPrompt] = useState("");
  const [workspaceLayout, setWorkspaceLayout] = useLocalStorage(
    "prompster.chat.workspace-layout",
    [62, 38],
  );
  const [canShowWorkspace, setCanShowWorkspace] = useState(() =>
    typeof window === "undefined"
      ? true
      : window.matchMedia("(min-width: 1024px)").matches,
  );
  const scrollViewportRef = useRef<HTMLDivElement>(null);
  const userCurationTrackPlayerRef = useRef<
    ((event: UserCurationEventResponse) => void) | null
  >(null);
  const [userCurationPlaybackState, setUserCurationPlaybackState] =
    useState<UserCurationTrackPlaybackState>({
      activeTrackUri: null,
      canControlPlayback: false,
      isPlaying: false,
    });
  const { showScrollToBottomButton, scrollToBottom } =
    useStickyScroll(scrollViewportRef);
  const pendingFollowUp = getPendingFollowUpQuestion(entries);
  const showThinkingPlaceholder = shouldShowThinkingPlaceholder(
    entries,
    isStreaming,
  );

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

  const renderEntry = (entry: ChatEntry, previousEntry?: ChatEntry) => {
    switch (entry.kind) {
      case "user_message":
        return <UserChatMessage key={entry.id} text={entry.content} />;

      case "assistant_message":
        return (
          <AssistantChatMessage
            key={entry.id}
            text={entry.content}
            isStreaming={entry.isStreaming}
            attachedAbove={previousEntry?.kind === "tool_call_group"}
          />
        );

      case "tool_call_group":
        return (
          <div key={entry.id} className="flex max-w-[82%] flex-col px-1 py-2">
            <ToolCallAccordion
              calls={toToolCallItems(entry)}
              defaultOpen={entry.calls.some((call) => call.state === "pending")}
            />
          </div>
        );

      case "follow_up_question_group": {
        const hasPendingQuestion = entry.questions.some(
          (question) => question.state === "pending",
        );

        if (hasPendingQuestion) return null;

        const currentQuestion = entry.questions.find(
          (question) => question.state === "pending",
        );

        return (
          <FollowUpQuestionGroup
            key={entry.id}
            group={entry}
            draftValue={
              currentQuestion ? (followUpDrafts[currentQuestion.id] ?? "") : ""
            }
            disabled={isStreaming}
            onDraftChange={updateFollowUpDraft}
            onAnswer={(question, answer, option) =>
              answerFollowUp(entry.id, question, answer, option)
            }
            onSkip={() => skipFollowUps(entry.id)}
            className="max-w-[82%]"
          />
        );
      }
    }
  };

  const chatPane = (
    <section className="flex h-full min-h-0 min-w-0 flex-1 flex-col">
      <ChatPageHeader
        session={session}
        title={title}
        isLoading={isLoadingSession}
        isTitlePending={isTitlePending}
        onSessionDeleted={() =>
          navigate("/new", { state: { newChatAt: Date.now() } })
        }
      />

      <main className="relative min-h-0 flex-1 overflow-hidden">
        <ScrollArea className="h-full min-h-0" viewportRef={scrollViewportRef}>
          <div className="px-4 sm:px-8">
            <div className="mx-auto flex w-full max-w-4xl flex-col">
              <div className="flex flex-col gap-4 px-1 pt-1 sm:px-2">
                {isLoadingSession ? (
                  <>
                    <ChatMessageSkeleton variant="user" />
                    <ChatMessageSkeleton variant="assistant" />
                  </>
                ) : (
                  <>
                    {isError && (
                      <p className="px-1 py-2 text-sm text-destructive">
                        Session konnte nicht geladen werden.
                      </p>
                    )}
                    {entries.map((entry, index) =>
                      renderEntry(entry, entries[index - 1]),
                    )}
                    {showThinkingPlaceholder && (
                      <ChatThinkingIndicator className="px-1 py-2" />
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
        </ScrollArea>
        <button
          type="button"
          onClick={() => scrollToBottom()}
          aria-label="Zu neuen Nachrichten scrollen"
          aria-hidden={!showScrollToBottomButton}
          tabIndex={showScrollToBottomButton ? 0 : -1}
          className={cn(
            "absolute bottom-4 left-1/2 z-20 flex size-9 -translate-x-1/2 items-center justify-center rounded-full border border-white/15 bg-background/90 text-foreground shadow-lg shadow-black/30 backdrop-blur transition-all duration-200 ease-out hover:bg-background hover:border-white/25",
            showScrollToBottomButton
              ? "opacity-100"
              : "pointer-events-none translate-y-2 opacity-0",
          )}
        >
          <ChevronDown className="size-4" />
        </button>
      </main>

      <div className="shrink-0 bg-gradient-to-t from-background via-background/85 to-transparent px-4 pb-4 pt-6 sm:px-8 sm:pb-3">
        <div className="mx-auto w-full max-w-4xl">
          <UserCurationEventContext
            sessionId={sessionId}
            events={session?.unconsumedUserCurationEvents ?? []}
            activeTrackUri={userCurationPlaybackState.activeTrackUri}
            isPlaybackActive={userCurationPlaybackState.isPlaying}
            onToggleTrackPlayback={
              userCurationPlaybackState.canControlPlayback
                ? toggleUserCurationEventTrackPlayback
                : undefined
            }
          />
          {pendingFollowUp ? (
            <FollowUpQuestionGroup
              group={pendingFollowUp.group}
              draftValue={followUpDrafts[pendingFollowUp.question.id] ?? ""}
              disabled={isStreaming}
              onDraftChange={updateFollowUpDraft}
              onAnswer={(question, answer, option) =>
                answerFollowUp(
                  pendingFollowUp.group.id,
                  question,
                  answer,
                  option,
                )
              }
              onSkip={() => skipFollowUps(pendingFollowUp.group.id)}
              className="px-0 pt-0"
            />
          ) : null}
          <ChatInputBox
            value={prompt}
            onChange={setPrompt}
            onSubmit={sendMessage}
            onStop={stopMessage}
            placeholder="Deine Antwort ..."
            sendButtonAriaLabel="Nachricht senden"
            className={cn(
              "rounded-3xl border border-border/50 bg-card/70 p-4 shadow-2xl shadow-black/20",
            )}
            textareaClassName="max-h-40"
            rows={1}
            disabled={!sessionId || isLoadingSession || isError}
            isSubmitting={isStreaming}
            isStopping={isStopping}
          />
        </div>
      </div>
    </section>
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
            minSize="45%"
          >
            {chatPane}
          </ResizablePanel>
          <ResizableHandle withHandle className="bg-white/[0.06]" />
          <ResizablePanel
            id="workspace"
            defaultSize={workspaceLayout[1] ?? 38}
            minSize="28%"
            maxSize="52%"
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
        <div className="relative z-10 flex h-full">{chatPane}</div>
      )}
    </div>
  );
};
