import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, FolderOpen, Import, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";

const MAX_LENGTH = 500;

export const HomePage = () => {
  const [prompt, setPrompt] = useState("");
  const navigate = useNavigate();

  const startChat = () => {
    navigate("/deck/mock", { state: { prompt } });
  };

  const isPromptEmpty = prompt.trim().length === 0;

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_10%_5%,_hsl(141_78%_26%)_0%,_transparent_40%),radial-gradient(circle_at_88%_8%,_hsl(154_66%_20%)_0%,_transparent_34%),linear-gradient(165deg,_hsl(222_46%_8%)_0%,_hsl(222_52%_5%)_100%)] text-foreground">
      <main className="mx-auto flex min-h-screen w-full max-w-4xl flex-col justify-center px-4 py-10 sm:px-8 sm:py-14">
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
              Beschreib dein Wunsch-Deck in einem Satz. Der Agent fragt gezielt
              nach und erstellt daraus Schritt fur Schritt dein Deck.
            </p>
          </div>

          <div className="rounded-2xl border border-border/60 bg-card/55 p-4 backdrop-blur-md sm:p-5">
            <Textarea
              className="min-h-30 resize-none border-none bg-transparent p-0 text-sm shadow-none focus-visible:ring-0"
              maxLength={MAX_LENGTH}
              placeholder='z.B. "Hip-Hop Klassiker der 90er fur 60 Karten" oder "Eurovision Hits 2000-2020"'
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
            />

            <Separator className="my-3" />

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

          <div className="flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-sm text-muted-foreground">
            <button
              type="button"
              className="inline-flex items-center gap-1.5 transition-colors hover:text-foreground"
            >
              <FolderOpen className="size-4 text-primary" />
              Vorhandenes Deck offnen
            </button>
            <button
              type="button"
              className="inline-flex items-center gap-1.5 transition-colors hover:text-foreground"
            >
              <Import className="size-4 text-primary" />
              Aus Spotify-Playlist importieren
            </button>
          </div>
        </section>
      </main>
    </div>
  );
};
