import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { ChatInputBox } from "@/components/chat-input-box";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

type ChatRole = "assistant" | "user";

type ChatMessage = {
  id: string;
  role: ChatRole;
  text: string;
};

export const HomePage = () => {
  const [prompt, setPrompt] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const location = useLocation();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const hasChatStarted = messages.length > 0;

  useEffect(() => {
    if (location.state && "newChatAt" in location.state) {
      setPrompt("");
      setMessages([]);
    }
  }, [location.state]);

  useEffect(() => {
    if (!hasChatStarted) return;

    messagesEndRef.current?.scrollIntoView({ block: "end" });
  }, [hasChatStarted, messages]);

  const sendMessage = (text: string) => {
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
  };

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
    <div className="home-page-background min-h-dvh text-foreground">
      <main
        className={cn(
          "relative z-10 flex min-h-dvh flex-col px-4 sm:px-8",
          hasChatStarted ? "py-5 sm:py-6" : "justify-center py-10 sm:py-14",
        )}
      >
        {!hasChatStarted ? (
          <div className="mx-auto w-full max-w-4xl -translate-y-6 sm:-translate-y-8">
            <section className="space-y-8">
              <div className="space-y-4 text-center sm:space-y-5">
                <Badge
                  variant="secondary"
                  className="mx-auto w-fit gap-1 px-2.5 py-1"
                >
                  <Sparkles className="size-3.5" />
                  Neues Karten-Deck
                </Badge>
                <h1 className="mx-auto max-w-3xl text-4xl font-semibold tracking-tight sm:text-6xl">
                  Welche Musik soll dein Deck haben?
                </h1>
                <p className="mx-auto max-w-2xl text-sm text-muted-foreground sm:text-lg">
                  Beschreib dein Wunsch-Deck in einem Satz. Der Agent fragt
                  gezielt nach und erstellt daraus Schritt fur Schritt dein
                  Deck.
                </p>
              </div>

              <ChatInputBox
                value={prompt}
                onChange={setPrompt}
                onSubmit={sendMessage}
                placeholder='z.B. "Hip-Hop Klassiker der 90er fur 60 Karten" oder "Eurovision Hits 2000-2020"'
                sendButtonAriaLabel="Chat starten"
              />
            </section>
          </div>
        ) : (
          <div className="mx-auto flex h-[calc(100dvh-2.5rem)] w-full max-w-4xl flex-col sm:h-[calc(100dvh-3rem)]">
            <div className="flex items-center justify-center pb-3">
              <Badge
                variant="secondary"
                className="w-fit gap-1 px-2.5 py-1"
              >
                <Sparkles className="size-3.5" />
                Neues Karten-Deck
              </Badge>
            </div>

            <ScrollArea className="min-h-0 flex-1">
              <div className="flex min-h-full flex-col justify-end gap-4 px-1 py-6 sm:px-2">
                {messages.map(renderMessage)}
                <div ref={messagesEndRef} />
              </div>
            </ScrollArea>

            <div className="pt-3">
              <ChatInputBox
                value={prompt}
                onChange={setPrompt}
                onSubmit={sendMessage}
                placeholder="Antworte oder frag..."
                sendButtonAriaLabel="Nachricht senden"
                className="rounded-3xl border border-border/50 bg-card/70 p-4 shadow-2xl shadow-black/20"
                textareaClassName="max-h-40"
                rows={1}
              />
            </div>
          </div>
        )}
      </main>

    </div>
  );
};
