import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "../components/Button";
import { TemplateCard } from "../components/TemplateCard";

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

  return (
    <div className="flex min-h-screen flex-col bg-[radial-gradient(circle_at_top,_#2D2D44_0%,_#1A1A2E_45%,_#16213E_100%)] text-[var(--beatline-text)]">
      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col justify-center px-6 py-16 sm:px-10">
        <p className="text-center text-xs font-semibold uppercase tracking-[0.24em] text-[var(--beatline-muted)]">
          Neues Karten-Deck
        </p>
        <h1 className="mx-auto mt-6 max-w-5xl text-center text-4xl font-bold tracking-tight text-[var(--beatline-text)] sm:text-6xl">
          Welche Musik soll dein Deck haben?
        </h1>
        <p className="mx-auto mt-7 max-w-2xl text-center text-lg leading-relaxed text-[var(--beatline-muted)]">
          Beschreib dein Wunsch-Deck in einem Satz. Der Bot stellt Rückfragen
          und baut die Karten Schritt für Schritt mit dir auf.
        </p>

        <section className="mx-auto mt-12 w-full rounded-2xl border border-[var(--beatline-border)] bg-[var(--beatline-surface)]/85 p-4 shadow-[0_16px_60px_rgba(0,0,0,0.35)] backdrop-blur-sm sm:p-5">
          <div className="rounded-xl border border-[var(--beatline-border)] bg-[var(--beatline-bg)] p-4 sm:p-5">
            <textarea
              className="h-24 w-full resize-none bg-transparent text-base leading-relaxed text-[var(--beatline-text)] outline-none placeholder:text-[var(--beatline-subtle)]"
              maxLength={MAX_LENGTH}
              placeholder='z.B. „Hip-Hop Klassiker der 90er für 60 Karten" oder „Eurovision Hits 2000-2020"'
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
            />

            <div className="mt-4 flex items-center justify-end gap-4">
              <span className="text-xs font-medium text-[var(--beatline-subtle)]">
                {prompt.length} / {MAX_LENGTH}
              </span>
              <Button onClick={startChat}>Chat starten →</Button>
            </div>
          </div>
        </section>

        <p className="mt-11 text-center text-xs font-semibold uppercase tracking-[0.22em] text-[var(--beatline-muted)]">
          Oder starte mit einer Vorlage
        </p>
        <section className="mx-auto mt-5 grid w-full grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {templateDecks.map((deck) => (
            <TemplateCard
              key={deck.title}
              title={deck.title}
              cards={deck.cards}
              onClick={() => chooseTemplate(deck.prompt)}
            />
          ))}
        </section>
      </main>
    </div>
  );
};
