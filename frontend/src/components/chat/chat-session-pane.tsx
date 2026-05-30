import { useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import { useNavigate } from "react-router-dom";

import type {
  SessionResponse,
  UserCurationEventResponse,
} from "@/api/generated/model";
import { AssistantChatMessage } from "@/components/chat/assistant-chat-message";
import { ChatInputBox } from "@/components/chat/chat-input-box";
import { ChatMessageSkeleton } from "@/components/chat/chat-message-skeleton";
import { ChatPageHeader } from "@/components/chat/chat-page-header";
import { ChatThinkingIndicator } from "@/components/chat/chat-thinking-indicator";
import { ToolCallAccordion } from "@/components/chat/tool-call-sequence";
import { ScrollArea } from "@/components/ui/scroll-area";
import { UserChatMessage } from "@/components/chat/user-chat-message";
import { UserCurationEventContext } from "@/components/chat/user-curation";
import { useStickyScroll } from "@/hooks/useStickyScroll";
import { cn } from "@/lib/utils";
import {
  type ChatEntry,
  type PendingInput,
  toToolCallItems,
} from "@/pages/chat-page.state";

type UserCurationTrackPlaybackState = {
  activeTrackUri: string | null;
  canControlPlayback: boolean;
  isPlaying: boolean;
};

type ChatSessionPaneProps = {
  sessionId: string;
  session?: SessionResponse;
  title?: string;
  entries: ChatEntry[];
  isTitlePending: boolean;
  isStreaming: boolean;
  isStopping: boolean;
  pendingInput: PendingInput | null;
  isLoadingSession: boolean;
  isError: boolean;
  sendMessage: (text: string) => void;
  stopMessage: () => void;
  userCurationPlaybackState: UserCurationTrackPlaybackState;
  onToggleUserCurationTrackPlayback?: (
    event: UserCurationEventResponse,
  ) => void;
};

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

export const ChatSessionPane = ({
  sessionId,
  session,
  title,
  entries,
  isTitlePending,
  isStreaming,
  isStopping,
  pendingInput,
  isLoadingSession,
  isError,
  sendMessage,
  stopMessage,
  userCurationPlaybackState,
  onToggleUserCurationTrackPlayback,
}: ChatSessionPaneProps) => {
  const navigate = useNavigate();
  const [prompt, setPrompt] = useState("");
  const scrollViewportRef = useRef<HTMLDivElement>(null);
  const { showScrollToBottomButton, scrollToBottom } =
    useStickyScroll(scrollViewportRef);
  const showThinkingPlaceholder = shouldShowThinkingPlaceholder(
    entries,
    isStreaming,
  );
  const isOnboardingQuestionPending =
    pendingInput?.kind === "onboarding_question" &&
    Boolean(pendingInput.questionId);

  const submitPrompt = (text: string) => {
    sendMessage(text);
  };

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
    }
  };

  return (
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
                ? onToggleUserCurationTrackPlayback
                : undefined
            }
          />
          <ChatInputBox
            value={prompt}
            onChange={setPrompt}
            onSubmit={submitPrompt}
            onStop={stopMessage}
            placeholder="Deine Antwort ..."
            sendButtonAriaLabel="Nachricht senden"
            className="rounded-3xl border border-border/50 bg-card/70 p-4 shadow-2xl shadow-black/20"
            textareaClassName="max-h-40"
            rows={1}
            disabled={
              !sessionId ||
              isLoadingSession ||
              isError ||
              isOnboardingQuestionPending
            }
            isSubmitting={isStreaming}
            isStopping={isStopping}
          />
        </div>
      </div>
    </section>
  );
};
