import { useMemo, useState } from "react";
import { useLocation, useParams } from "react-router-dom";

import type { SessionResponse } from "@/api/generated/model";
import { AssistantChatMessage } from "@/components/chat/assistant-chat-message";
import { ChatInputBox } from "@/components/chat/chat-input-box";
import { ChatMessageSkeleton } from "@/components/chat/chat-message-skeleton";
import { ChatPageHeader } from "@/components/chat/chat-page-header";
import { FollowUpQuestionGroup } from "@/components/chat/follow-up-question-group";
import { ToolCallAccordion } from "@/components/chat/tool-call-accordion";
import { UserChatMessage } from "@/components/chat/user-chat-message";
import { useAutoScrollToBottom } from "@/hooks/useAutoScrollToBottom";
import { cn } from "@/lib/utils";

import { useChatSession } from "./chat-page.hook";
import {
  getScrollKey,
  toToolCallItems,
  type ChatEntry,
} from "./chat-page.state";

type ChatRouteState = {
  session?: SessionResponse;
  streamInitialResponse?: boolean;
};

export const ChatPage = () => {
  const { chatId } = useParams();
  const sessionId = chatId ?? "";
  const location = useLocation();
  const routeState = location.state as ChatRouteState | null;

  const initialSession = useMemo(() => {
    if (routeState?.session?.id !== sessionId) return undefined;
    return routeState.session;
  }, [routeState?.session, sessionId]);

  const {
    title,
    entries,
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
  const scrollDependency = entries.map(getScrollKey).join("|");
  const messagesEndRef =
    useAutoScrollToBottom<HTMLDivElement>(scrollDependency);

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

  return (
    <div className="chat-page-background flex h-dvh overflow-hidden text-foreground">
      <div className="relative z-10 min-h-0 flex-1">
        <section className="flex h-full min-h-0 min-w-0 flex-1 flex-col">
          <ChatPageHeader title={headerTitle} isLoading={isLoadingSession} />

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
      </div>
    </div>
  );
};
