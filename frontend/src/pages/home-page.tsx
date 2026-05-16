import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { ChatInputBox } from "@/components/chat-input-box";

export const HomePage = () => {
  const [prompt, setPrompt] = useState("");
  const navigate = useNavigate();

  const startChat = (text: string) => {
    const chatId = crypto.randomUUID();
    navigate(`/chat/${chatId}`, { state: { initialPrompt: text } });
  };

  return (
    <div className="home-page-background min-h-dvh text-foreground">
      <main className="relative z-10 flex min-h-dvh flex-col justify-center px-4 py-10 sm:px-8 sm:py-14">
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
                gezielt nach und erstellt daraus Schritt fur Schritt dein Deck.
              </p>
            </div>

            <ChatInputBox
              value={prompt}
              onChange={setPrompt}
              onSubmit={startChat}
              placeholder='z.B. "Hip-Hop Klassiker der 90er fur 60 Karten" oder "Eurovision Hits 2000-2020"'
              sendButtonAriaLabel="Chat starten"
            />
          </section>
        </div>
      </main>
    </div>
  );
};
