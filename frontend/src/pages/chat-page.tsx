import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";

import type { MessageResponse, SessionResponse } from "@/api/generated/model";
import {
  getGetSessionQueryKey,
  getListSessionsQueryKey,
  useGetSession,
} from "@/api/generated/session-api";
import { streamSendMessage } from "@/api/session-stream";
import { AssistantChatMessage } from "@/components/assistant-chat-message";
import { ChatInputBox } from "@/components/chat-input-box";
import { ChatPageHeader } from "@/components/chat-page-header";
import { UserChatMessage } from "@/components/user-chat-message";
import { useAutoScrollToBottom } from "@/hooks/useAutoScrollToBottom";
import { cn } from "@/lib/utils";

type ChatRouteState = {
  session?: SessionResponse;
  streamInitialResponse?: boolean;
};

type ChatMessage = {
  id: string;
  role: MessageResponse["role"];
  text: string;
  isStreaming?: boolean;
};

const toChatMessage = (message: MessageResponse): ChatMessage => ({
  id: message.id,
  role: message.role,
  text: message.content,
});

export const ChatPage = () => {
  const { chatId } = useParams();
  const sessionId = chatId ?? "";
  const location = useLocation();
  const routeState = location.state as ChatRouteState | null;
  const queryClient = useQueryClient();
  const [prompt, setPrompt] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isSending, setIsSending] = useState(false);
  const loadedSessionIdRef = useRef<string | undefined>(undefined);
  const initialStreamStartedRef = useRef(false);
  const abortControllerRef = useRef<AbortController | null>(null);

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

  const scrollDependency = messages
    .map((message) => `${message.id}:${message.text.length}`)
    .join("|");
  const messagesEndRef =
    useAutoScrollToBottom<HTMLDivElement>(scrollDependency);

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    if (!session || loadedSessionIdRef.current === session.id) return;

    loadedSessionIdRef.current = session.id;
    queueMicrotask(() => {
      setMessages(session.messages.map(toChatMessage));
    });
  }, [session]);

  const invalidateSessionQueries = useCallback(async () => {
    if (!sessionId) return;

    await Promise.all([
      queryClient.invalidateQueries({
        queryKey: getGetSessionQueryKey(sessionId),
      }),
      queryClient.invalidateQueries({ queryKey: getListSessionsQueryKey() }),
    ]);
  }, [queryClient, sessionId]);

  const streamAssistantResponse = useCallback(
    async (text: string, options?: { appendUserMessage?: boolean }) => {
      if (!sessionId || isSending) return;

      const shouldAppendUserMessage = options?.appendUserMessage ?? true;
      const controller = new AbortController();
      const assistantMessageId = `assistant-${crypto.randomUUID()}`;

      abortControllerRef.current = controller;
      setIsSending(true);
      setMessages((currentMessages) => [
        ...currentMessages,
        ...(shouldAppendUserMessage
          ? [
              {
                id: `user-${crypto.randomUUID()}`,
                role: "user" as const,
                text,
              },
            ]
          : []),
        {
          id: assistantMessageId,
          role: "assistant",
          text: "",
          isStreaming: true,
        },
      ]);

      try {
        await streamSendMessage(
          sessionId,
          { content: text },
          {
            signal: controller.signal,
            onChunk: (chunk) => {
              setMessages((currentMessages) =>
                currentMessages.map((message) =>
                  message.id === assistantMessageId
                    ? { ...message, text: message.text + chunk }
                    : message,
                ),
              );
            },
          },
        );

        setMessages((currentMessages) =>
          currentMessages.map((message) =>
            message.id === assistantMessageId
              ? { ...message, isStreaming: false }
              : message,
          ),
        );
        await invalidateSessionQueries();
      } catch {
        if (!controller.signal.aborted) {
          setMessages((currentMessages) =>
            currentMessages.map((message) =>
              message.id === assistantMessageId
                ? {
                    ...message,
                    text:
                      message.text ||
                      "Die Antwort konnte nicht geladen werden.",
                    isStreaming: false,
                  }
                : message,
            ),
          );
        }
      } finally {
        if (abortControllerRef.current === controller) {
          abortControllerRef.current = null;
        }
        setIsSending(false);
      }
    },
    [invalidateSessionQueries, isSending, sessionId],
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

    const latestMessage = session.messages.at(-1);
    if (!latestMessage || latestMessage.role !== "user") return;

    initialStreamStartedRef.current = true;
    const timeoutId = window.setTimeout(() => {
      void streamAssistantResponse(latestMessage.content, {
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

  const isLoadingSession = isLoading && messages.length === 0;
  const title = session?.title ?? "Neues Karten-Deck";

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

                {messages.map((message) =>
                  message.role === "user" ? (
                    <UserChatMessage key={message.id} text={message.text} />
                  ) : (
                    <AssistantChatMessage
                      key={message.id}
                      text={message.text}
                      isStreaming={message.isStreaming}
                    />
                  ),
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
