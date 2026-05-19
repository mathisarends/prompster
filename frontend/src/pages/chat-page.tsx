import {
  useCallback,
  useEffect,
  useMemo,
  useReducer,
  useRef,
  useState,
} from "react";
import { useLocation, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";

import type {
  FollowUpQuestionResponse,
  FollowUpRequest,
  SessionResponse,
} from "@/api/generated/model";
import {
  getGetSessionQueryKey,
  getListSessionsQueryKey,
  useGetSession,
} from "@/api/generated/session-api";
import { streamFollowUp, streamSendMessage } from "@/api/session-stream";
import { AssistantChatMessage } from "@/components/assistant-chat-message";
import { ChatInputBox } from "@/components/chat-input-box";
import { ChatPageHeader } from "@/components/chat-page-header";
import { FollowUpQuestionGroup } from "@/components/follow-up-question-group";
import type { FollowUpQuestionOption } from "@/components/follow-up-question-flow";
import { ToolCallAccordion } from "@/components/tool-call-accordion";
import { UserChatMessage } from "@/components/user-chat-message";
import { useAutoScrollToBottom } from "@/hooks/useAutoScrollToBottom";
import { cn } from "@/lib/utils";

import {
  chatReducer,
  createInitialChatState,
  getLatestUserMessageContent,
  toToolCallItems,
  type ChatEntry,
} from "./chat-page.state";

type ChatRouteState = {
  session?: SessionResponse;
  streamInitialResponse?: boolean;
};

type StreamOptions = Parameters<typeof streamSendMessage>[2];

const getStreamErrorMessage = (error: unknown) => {
  if (error instanceof Error && error.message) return error.message;
  return "Die Antwort konnte nicht geladen werden.";
};

const getScrollKey = (entry: ChatEntry) => {
  switch (entry.kind) {
    case "user_message":
    case "assistant_message":
      return `${entry.id}:${entry.content.length}:${entry.kind === "assistant_message" && entry.isStreaming ? "streaming" : "done"}`;
    case "tool_call_group":
      return `${entry.id}:${entry.calls
        .map(
          (call) =>
            `${call.id}:${call.state}:${call.result?.length ?? 0}:${call.error?.length ?? 0}`,
        )
        .join(",")}`;
    case "follow_up_question_group":
      return `${entry.id}:${entry.questions
        .map(
          (question) =>
            `${question.id}:${question.state}:${question.answerText?.length ?? 0}`,
        )
        .join(",")}`;
  }
};

export const ChatPage = () => {
  const { chatId } = useParams();
  const sessionId = chatId ?? "";
  const location = useLocation();
  const routeState = location.state as ChatRouteState | null;
  const queryClient = useQueryClient();
  const [prompt, setPrompt] = useState("");
  const [chatState, dispatch] = useReducer(
    chatReducer,
    undefined,
    createInitialChatState,
  );
  const initialStreamStartedRef = useRef(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const isStreamingRef = useRef(false);

  const initialSession = useMemo(() => {
    if (routeState?.session?.id !== sessionId) return undefined;
    return routeState.session;
  }, [routeState?.session, sessionId]);

  const {
    data: session,
    isError,
    isLoading,
  } = useGetSession(sessionId, {
    query: {
      enabled: Boolean(sessionId),
      initialData: initialSession,
    },
  });

  const isSending = chatState.isStreaming;
  const scrollDependency = chatState.entries.map(getScrollKey).join("|");
  const messagesEndRef =
    useAutoScrollToBottom<HTMLDivElement>(scrollDependency);

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    isStreamingRef.current = false;
    initialStreamStartedRef.current = false;
    dispatch({ type: "session/reset" });
  }, [sessionId]);

  useEffect(() => {
    isStreamingRef.current = chatState.isStreaming;
  }, [chatState.isStreaming]);

  useEffect(() => {
    if (!session || session.id !== sessionId || chatState.isStreaming) return;

    dispatch({ type: "session/loaded", session });
  }, [chatState.isStreaming, session, sessionId]);

  const invalidateSessionQueries = useCallback(async () => {
    if (!sessionId) return;

    await Promise.all([
      queryClient.invalidateQueries({
        queryKey: getGetSessionQueryKey(sessionId),
      }),
      queryClient.invalidateQueries({ queryKey: getListSessionsQueryKey() }),
    ]);
  }, [queryClient, sessionId]);

  const runEventStream = useCallback(
    async (
      startAction: Parameters<typeof dispatch>[0],
      streamRequest: (options: StreamOptions) => Promise<void>,
    ) => {
      if (!sessionId || isStreamingRef.current) return;

      const controller = new AbortController();
      let streamErrorReceived = false;

      isStreamingRef.current = true;
      abortControllerRef.current = controller;
      dispatch(startAction);

      try {
        await streamRequest({
          signal: controller.signal,
          onEvent: (event) => {
            if (event.type === "error") streamErrorReceived = true;
            dispatch({ type: "stream/event", event });
          },
        });

        await invalidateSessionQueries();
      } catch (error) {
        if (!controller.signal.aborted && !streamErrorReceived) {
          dispatch({
            type: "stream/failed",
            message: getStreamErrorMessage(error),
          });
        }
      } finally {
        if (abortControllerRef.current === controller) {
          abortControllerRef.current = null;
        }
        isStreamingRef.current = false;
        dispatch({ type: "stream/finished" });
      }
    },
    [invalidateSessionQueries, sessionId],
  );

  const streamAssistantResponse = useCallback(
    async (text: string, options?: { appendUserMessage?: boolean }) => {
      const shouldAppendUserMessage = options?.appendUserMessage ?? true;

      await runEventStream(
        {
          type: "stream/started",
          userMessageText: shouldAppendUserMessage ? text : undefined,
          skipPendingFollowUps: shouldAppendUserMessage,
        },
        (streamOptions) =>
          streamSendMessage(sessionId, { content: text }, streamOptions),
      );
    },
    [runEventStream, sessionId],
  );

  const streamFollowUpResponse = useCallback(
    async (body: FollowUpRequest) => {
      await runEventStream({ type: "stream/started" }, (streamOptions) =>
        streamFollowUp(sessionId, body, streamOptions),
      );
    },
    [runEventStream, sessionId],
  );

  useEffect(() => {
    if (
      !routeState?.streamInitialResponse ||
      initialStreamStartedRef.current ||
      !session ||
      isSending
    ) {
      return;
    }

    const latestUserMessageContent = getLatestUserMessageContent(session);
    if (!latestUserMessageContent) return;

    initialStreamStartedRef.current = true;
    const timeoutId = window.setTimeout(() => {
      void streamAssistantResponse(latestUserMessageContent, {
        appendUserMessage: false,
      });
    }, 0);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [
    isSending,
    routeState?.streamInitialResponse,
    session,
    streamAssistantResponse,
  ]);

  const sendChatMessage = useCallback(
    (text: string) => streamAssistantResponse(text),
    [streamAssistantResponse],
  );

  const answerFollowUp = useCallback(
    (
      groupId: string,
      question: FollowUpQuestionResponse,
      answer: string,
      option?: FollowUpQuestionOption,
    ) => {
      if (isStreamingRef.current) return;

      dispatch({
        type: "follow-up/answered",
        groupId,
        questionId: question.id,
        answerText: answer,
        optionId: option?.id,
      });
      void streamFollowUpResponse({
        action: "answer",
        answers: [
          option
            ? { questionId: question.id, optionId: option.id }
            : { questionId: question.id, text: answer },
        ],
      });
    },
    [streamFollowUpResponse],
  );

  const skipFollowUps = useCallback(
    (groupId: string) => {
      if (isStreamingRef.current) return;

      dispatch({ type: "follow-up/skipped", groupId });
      void streamFollowUpResponse({ action: "skip_remaining" });
    },
    [streamFollowUpResponse],
  );

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
              currentQuestion
                ? (chatState.followUpDrafts[currentQuestion.id] ?? "")
                : ""
            }
            disabled={isSending}
            onDraftChange={(questionId, value) =>
              dispatch({
                type: "follow-up/draft-changed",
                questionId,
                value,
              })
            }
            onAnswer={(question, answer, option) =>
              answerFollowUp(entry.id, question, answer, option)
            }
            onSkip={() => skipFollowUps(entry.id)}
          />
        );
      }
    }
  };

  const isLoadingSession = isLoading && chatState.entries.length === 0;
  const title = chatState.title ?? session?.title ?? "Neues Karten-Deck";

  return (
    <div className="chat-page-background flex h-dvh overflow-hidden text-foreground">
      <div className="relative z-10 min-h-0 flex-1">
        <section className="flex h-full min-h-0 min-w-0 flex-1 flex-col">
          <ChatPageHeader title={title} />

          <main className="prompster-scrollbar min-h-0 flex-1 overflow-y-auto px-4 sm:px-8">
            <div className="mx-auto flex w-full max-w-4xl flex-col">
              <div className="flex flex-col gap-4 px-1 pt-1 sm:px-2">
                {isLoadingSession ? (
                  <p className="px-1 py-2 text-sm text-muted-foreground">
                    Lade Session...
                  </p>
                ) : isError ? (
                  <p className="px-1 py-2 text-sm text-destructive">
                    Session konnte nicht geladen werden.
                  </p>
                ) : null}

                {chatState.entries.map(renderEntry)}
                <div ref={messagesEndRef} />
              </div>
            </div>
          </main>

          <div className="shrink-0 bg-gradient-to-t from-background via-background/85 to-transparent px-4 pb-4 pt-6 sm:px-8 sm:pb-3">
            <div className="mx-auto w-full max-w-4xl">
              <ChatInputBox
                value={prompt}
                onChange={setPrompt}
                onSubmit={sendChatMessage}
                placeholder="Deine Antwort ..."
                sendButtonAriaLabel="Nachricht senden"
                className={cn(
                  "rounded-3xl border border-border/50 bg-card/70 p-4 shadow-2xl shadow-black/20",
                )}
                textareaClassName="max-h-40"
                rows={1}
                disabled={!sessionId || isLoadingSession || isError}
                isSubmitting={isSending}
              />
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};
