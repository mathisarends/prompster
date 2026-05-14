import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { NavigationSidebar } from "@/components/navigation-sidebar";
import type { ChatHistoryEntry } from "@/lib/mockChats";
import { cn } from "@/lib/utils";

const MAX_LENGTH = 500;

export const HomePage = () => {
  const [prompt, setPrompt] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeChatId, setActiveChatId] = useState<string | undefined>();
  const navigate = useNavigate();

  const startChat = () => {
    navigate("/deck/mock", { state: { prompt } });
  };

  const isPromptEmpty = prompt.trim().length === 0;

  const handleSelectChat = (chat: ChatHistoryEntry) => {
    setActiveChatId(chat.id);
    navigate("/deck/mock", { state: { prompt: chat.title } });
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_10%_5%,_hsl(141_78%_26%)_0%,_transparent_40%),radial-gradient(circle_at_88%_8%,_hsl(154_50%_16%)_0%,_transparent_22%),linear-gradient(165deg,_hsl(222_46%_8%)_0%,_hsl(222_52%_5%)_100%)] text-foreground">
      <NavigationSidebar
        open={sidebarOpen}
        onToggle={() => setSidebarOpen((prev) => !prev)}
        onSelectChat={handleSelectChat}
        activeChatId={activeChatId}
      />

      <main
        className={cn(
          "flex min-h-screen flex-col justify-center px-4 py-10 transition-[padding] duration-300 ease-out sm:px-8 sm:py-14",
          sidebarOpen ? "sm:pl-80" : "sm:pl-24",
        )}
      >
        <div className="mx-auto w-full max-w-4xl">
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

            <div className="space-y-2">
              <div className="rounded-2xl bg-card/55 p-4 backdrop-blur-md sm:p-5">
                <Textarea
                  className="min-h-30 resize-none border-none bg-transparent p-0 text-sm shadow-none focus-visible:ring-0"
                  maxLength={MAX_LENGTH}
                  placeholder='z.B. "Hip-Hop Klassiker der 90er fur 60 Karten" oder "Eurovision Hits 2000-2020"'
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                />

                <div className="flex items-center justify-between gap-3">
                  <p className="text-xs text-muted-foreground">
                    {prompt.length} / {MAX_LENGTH}
                  </p>
                  <Button onClick={startChat} disabled={isPromptEmpty}>
                    Chat starten
                    <ArrowRight className="size-4" />
                  </Button>
                </div>
              </div>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
};
