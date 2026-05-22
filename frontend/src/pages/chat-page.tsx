import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";

import type { SessionResponse } from "@/api/generated/model";
import { AssistantChatMessage } from "@/components/chat/assistant-chat-message";
import { ChatInputBox } from "@/components/chat/chat-input-box";
import { ChatMessageSkeleton } from "@/components/chat/chat-message-skeleton";
import { ChatPageHeader } from "@/components/chat/chat-page-header";
import { DeckWorkspaceView } from "@/components/deck/deck-workspace-view";
import { FollowUpQuestionGroup } from "@/components/chat/follow-up-question-group";
import { ToolCallAccordion } from "@/components/chat/tool-call-accordion";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { UserChatMessage } from "@/components/chat/user-chat-message";
import { useAutoScrollToBottom } from "@/hooks/useAutoScrollToBottom";
import { useLocalStorage } from "@/hooks/useLocalStorage";
import { cn } from "@/lib/utils";

import {
  getScrollKey,
  toToolCallItems,
  type ChatEntry,
} from "./chat-page.state";
import { useChatSession } from "./chat-page.hook";

type ChatRouteState = {
  session?: SessionResponse;
  streamInitialResponse?: boolean;
};

export const ChatPage = () => {
  const { chatId } = useParams();
  const sessionId = chatId ?? "";
  const location = useLocation();
  const navigate = useNavigate();
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
    isStreaming,
    isLoadingSession,
    isError,
    sendMessage,
    answerFollowUp,
    skipFollowUps,
    updateFollowUpDraft,
  } = useChatSession({
    sessionId,
    initialSession,
    streamInitialResponse: Boolean(routeState?.streamInitialResponse),
  });

  const [prompt, setPrompt] = useState("");
  const [closedWorkspacePlaylistId, setClosedWorkspacePlaylistId] = useState<
    string | null
  >(null);
  const [workspaceLayout, setWorkspaceLayout] = useLocalStorage(
    "prompster.chat.workspace-layout",
    [62, 38],
  );
  const [canShowWorkspace, setCanShowWorkspace] = useState(() =>
    typeof window === "undefined"
      ? true
      : window.matchMedia("(min-width: 1024px)").matches,
  );
  const scrollDependency = entries.map(getScrollKey).join("|");
  const messagesEndRef =
    useAutoScrollToBottom<HTMLDivElement>(scrollDependency);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(min-width: 1024px)");
    const handleChange = (event: MediaQueryListEvent) => {
      setCanShowWorkspace(event.matches);
    };

    mediaQuery.addEventListener("change", handleChange);
    return () => mediaQuery.removeEventListener("change", handleChange);
  }, []);

  const renderEntry = (entry: ChatEntry) => {
    switch (entry.kind) {
      case "user_message":
        return <UserChatMessage key={entry.id} text={entry.content} />;

      case "assistant_message":
        return (
          <AssistantChatMessage
            key={entry.id}
            text={entry.content}
            isStreaming={entry.isStreaming}
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
          />
        );
      }
    }
  };

  const headerTitle = title ?? "Neues Karten-Deck";
  const isWorkspaceOpen = Boolean(
    playlist && playlist.id !== closedWorkspacePlaylistId,
  );
  const chatPane = (
    <section className="flex h-full min-h-0 min-w-0 flex-1 flex-col">
      <ChatPageHeader
        session={session}
        title={headerTitle}
        isLoading={isLoadingSession}
        onSessionDeleted={() =>
          navigate("/new", { state: { newChatAt: Date.now() } })
        }
      />

      <main className="prompster-scrollbar min-h-0 flex-1 overflow-y-auto px-4 sm:px-8">
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
                {entries.map(renderEntry)}
              </>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>
      </main>

      <div className="shrink-0 bg-gradient-to-t from-background via-background/85 to-transparent px-4 pb-4 pt-6 sm:px-8 sm:pb-3">
        <div className="mx-auto w-full max-w-4xl">
          <ChatInputBox
            value={prompt}
            onChange={setPrompt}
            onSubmit={sendMessage}
            placeholder="Deine Antwort ..."
            sendButtonAriaLabel="Nachricht senden"
            className={cn(
              "rounded-3xl border border-border/50 bg-card/70 p-4 shadow-2xl shadow-black/20",
            )}
            textareaClassName="max-h-40"
            rows={1}
            disabled={!sessionId || isLoadingSession || isError}
            isSubmitting={isStreaming}
          />
        </div>
      </div>
    </section>
  );

  return (
    <div className="chat-page-background h-dvh overflow-hidden text-foreground">
      {playlist && isWorkspaceOpen && canShowWorkspace ? (
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
              playlist={playlist}
              onClose={() => setClosedWorkspacePlaylistId(playlist.id)}
            />
          </ResizablePanel>
        </ResizablePanelGroup>
      ) : (
        <div className="relative z-10 flex h-full">{chatPane}</div>
      )}
    </div>
  );
};
