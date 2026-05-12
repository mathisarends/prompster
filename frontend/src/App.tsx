import { useState } from "react";
import { Button } from "./components/Button";
import { TemplateCard } from "./components/TemplateCard";

const templateDecks = [
  { title: "80er & 90er Pop", cards: "50 Karten" },
  { title: "Rock Klassiker", cards: "100 Karten" },
  { title: "Charts 2000-2020", cards: "60 Karten" },
  { title: "Eurovision", cards: "40 Karten" },
  { title: "Hip-Hop Hall of Fame", cards: "50 Karten" },
  { title: "Kindergeburtstag", cards: "30 Karten" },
];

const MAX_LENGTH = 500;

export const App = () => {
  const [prompt, setPrompt] = useState("");

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_#2D2D44_0%,_#1A1A2E_45%,_#16213E_100%)] text-[var(--beatline-text)]">
      <main className="mx-auto flex w-full max-w-5xl flex-col px-6 pb-10 pt-18 sm:px-10 sm:pt-24">
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
              <Button>Chat starten →</Button>
            </div>
          </div>
        </section>

        <p className="mt-11 text-center text-xs font-semibold uppercase tracking-[0.22em] text-[var(--beatline-muted)]">
          Oder starte mit einer Vorlage
        </p>
        <section className="mx-auto mt-5 grid w-full grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {templateDecks.map((deck) => (
            <TemplateCard key={deck.title} title={deck.title} cards={deck.cards} />
          ))}
        </section>

        <footer className="mx-auto mt-14 flex flex-wrap items-center justify-center gap-8 text-sm text-[var(--beatline-muted)]">
          <Button variant="ghost">Vorhandenes Deck öffnen</Button>
          <Button variant="ghost">Aus Spotify-Playlist importieren</Button>
        </footer>
      </main>
    </div>
  );
};
