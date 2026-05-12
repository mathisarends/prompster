import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowRight,
  CalendarRange,
  FolderOpen,
  Import,
  Sparkles,
  Waves,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";

const templateDecks = [
  {
    title: "80er & 90er Pop",
    cards: "50 Karten",
    prompt:
      "Erstelle mir ein Deck mit 50 Karten zu den größten Pop-Hits der 80er und 90er Jahre.",
  },
  {
    title: "Rock Klassiker",
    cards: "100 Karten",
    prompt:
      "Erstelle mir ein Deck mit 100 Karten zu den zeitlosen Rock-Klassikern aller Jahrzehnte.",
  },
  {
    title: "Charts 2000-2020",
    cards: "60 Karten",
    prompt:
      "Erstelle mir ein Deck mit 60 Karten zu den größten Chart-Hits von 2000 bis 2020.",
  },
  {
    title: "Eurovision",
    cards: "40 Karten",
    prompt:
      "Erstelle mir ein Deck mit 40 Karten zu unvergesslichen Eurovision Song Contest Beiträgen.",
  },
  {
    title: "Hip-Hop Hall of Fame",
    cards: "50 Karten",
    prompt:
      "Erstelle mir ein Deck mit 50 Karten zu den legendärsten Hip-Hop-Songs und Künstlern aller Zeiten.",
  },
  {
    title: "Kindergeburtstag",
    cards: "30 Karten",
    prompt:
      "Erstelle mir ein Deck mit 30 Karten zu fröhlichen, kinderfreundlichen Liedern für einen Kindergeburtstag.",
  },
];

const MAX_LENGTH = 500;

export const HomePage = () => {
  const [prompt, setPrompt] = useState("");
  const navigate = useNavigate();

  const startChat = () => {
    navigate("/deck/mock", { state: { prompt } });
  };

  const chooseTemplate = (templatePrompt: string) => {
    setPrompt(templatePrompt);
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

            <div className="mt-3 flex flex-wrap gap-2">
              <Badge variant="outline" className="gap-1.5 px-2.5 py-1">
                <Waves className="size-3.5" />
                Spotify
              </Badge>
              <Badge variant="outline" className="px-2.5 py-1">
                Sprache: DE
              </Badge>
              <Badge variant="outline" className="gap-1.5 px-2.5 py-1">
                <CalendarRange className="size-3.5" />
                Zeitraum
              </Badge>
            </div>

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

          <div className="space-y-3">
            <p className="text-center text-xs font-semibold tracking-[0.16em] text-muted-foreground uppercase">
              Oder starte mit einer Vorlage
            </p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {templateDecks.map((deck) => (
                <Card
                  key={deck.title}
                  size="sm"
                  role="button"
                  tabIndex={0}
                  className="cursor-pointer border border-border/65 bg-card/62 p-4 transition-all hover:-translate-y-0.5 hover:border-primary/50 hover:bg-card/85"
                  onClick={() => chooseTemplate(deck.prompt)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      chooseTemplate(deck.prompt);
                    }
                  }}
                >
                  <p className="text-base leading-tight font-semibold">
                    {deck.title}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {deck.cards}
                  </p>
                </Card>
              ))}
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
