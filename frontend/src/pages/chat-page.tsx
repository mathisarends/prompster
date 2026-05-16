import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { Sparkles } from "lucide-react";

import { ChatInputBox } from "@/components/chat-input-box";
import { cn } from "@/lib/utils";

type ChatRole = "assistant" | "user";

type ChatMessage = {
  id: string;
  role: ChatRole;
  text: string;
};

const getInitialPrompt = (state: unknown) => {
  if (!state || typeof state !== "object" || !("initialPrompt" in state)) {
    return undefined;
  }

  const initialPrompt = (state as { initialPrompt?: unknown }).initialPrompt;
  if (typeof initialPrompt !== "string") return undefined;

  const trimmedPrompt = initialPrompt.trim();
  return trimmedPrompt.length > 0 ? trimmedPrompt : undefined;
};

export const ChatPage = () => {
  const location = useLocation();
  const initialPrompt = getInitialPrompt(location.state);
  const [prompt, setPrompt] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    if (!initialPrompt) return [];

    return [
      {
        id: `user-${crypto.randomUUID()}`,
        role: "user",
        text: initialPrompt,
      },
      {
        id: `assistant-${crypto.randomUUID()}`,
        role: "assistant",
        text: "Verstanden. Ich stelle dir zuerst ein paar gezielte Fragen, damit das Deck sauber wird: Wie viele Karten soll es haben und sollen die Songs eher bekannt, nischig oder gemischt sein?",
      },
    ];
  });
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const sendMessage = useCallback((text: string) => {
    setMessages((currentMessages) => {
      const userMessage: ChatMessage = {
        id: `user-${crypto.randomUUID()}`,
        role: "user",
        text,
      };

      const assistantMessage: ChatMessage = {
        id: `assistant-${crypto.randomUUID()}`,
        role: "assistant",
        text:
          currentMessages.length === 0
            ? "Verstanden. Ich stelle dir zuerst ein paar gezielte Fragen, damit das Deck sauber wird: Wie viele Karten soll es haben und sollen die Songs eher bekannt, nischig oder gemischt sein?"
            : "Alles klar. Ich nehme das mit auf und verfeinere den Deck-Plan weiter.",
      };

      return [...currentMessages, userMessage, assistantMessage];
    });
  }, []);

  useEffect(() => {
    if (messages.length === 0) return;
    messagesEndRef.current?.scrollIntoView({ block: "end" });
  }, [messages]);

  const renderMessage = (message: ChatMessage) => (
    <div
      key={message.id}
      className={cn(
        "text-sm leading-relaxed sm:text-base",
        message.role === "user"
          ? "ml-auto max-w-[82%] rounded-2xl bg-white/10 px-4 py-3 text-foreground"
          : "max-w-[82%] px-1 py-2 text-muted-foreground",
      )}
    >
      {message.text}
    </div>
  );

  return (
    <div className="min-h-dvh bg-background text-foreground">
      <header className="fixed inset-x-0 top-0 z-20 flex h-14 items-center justify-center bg-background/80 backdrop-blur-md">
        <span className="inline-flex items-center gap-2.5 text-sm font-semibold text-foreground/85">
          <Sparkles className="size-3.5" />
          Neues Karten-Deck
        </span>
      </header>

      <main className="relative z-10 flex flex-col px-4 pb-40 pt-14 sm:px-8 sm:pb-44">
        <div className="mx-auto flex w-full max-w-4xl flex-col">
          <div className="flex flex-col gap-4 px-1 pt-8 sm:px-2">
            {messages.map(renderMessage)}
            <div ref={messagesEndRef} />
          </div>
        </div>
      </main>

      <div className="pointer-events-none fixed inset-x-0 bottom-0 z-10 bg-gradient-to-t from-background via-background/85 to-transparent pt-6">
        <div className="mx-auto w-full max-w-4xl px-4 pb-4 sm:px-8 sm:pb-6">
          <ChatInputBox
            value={prompt}
            onChange={setPrompt}
            onSubmit={sendMessage}
            placeholder="Deine Antwort ..."
            sendButtonAriaLabel="Nachricht senden"
            className="pointer-events-auto rounded-3xl border border-border/50 bg-card/70 p-4 shadow-2xl shadow-black/20"
            textareaClassName="max-h-40"
            rows={1}
          />
        </div>
      </div>
    </div>
  );
};
