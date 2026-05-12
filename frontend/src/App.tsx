const templateDecks = [
  { title: "80er & 90er Pop", cards: "50 Karten" },
  { title: "Rock Klassiker", cards: "100 Karten" },
  { title: "Charts 2000-2020", cards: "60 Karten" },
  { title: "Eurovision", cards: "40 Karten" },
  { title: "Hip-Hop Hall of Fame", cards: "50 Karten" },
  { title: "Kindergeburtstag", cards: "30 Karten" },
];

export const App = () => {
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
              maxLength={500}
              placeholder='z.B. „Hip-Hop Klassiker der 90er für 60 Karten" oder „Eurovision Hits 2000-2020"'
            />

            <div className="mt-4 flex flex-wrap items-center gap-2">
              <div className="ml-auto flex items-center gap-4">
                <span className="text-xs font-medium text-[var(--beatline-subtle)]">
                  0 / 500
                </span>
                <button
                  className="rounded-lg border border-[var(--beatline-gold-dark)] bg-[var(--beatline-gold)] px-4 py-2 text-sm font-semibold text-[#2D2D44] transition-colors hover:bg-[var(--beatline-gold-dark)]"
                  type="button"
                >
                  Chat starten →
                </button>
              </div>
            </div>
          </div>
        </section>

        <p className="mt-11 text-center text-xs font-semibold uppercase tracking-[0.22em] text-[var(--beatline-muted)]">
          Oder starte mit einer Vorlage
        </p>
        <section className="mx-auto mt-5 grid w-full grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {templateDecks.map((deck) => (
            <button
              className="group rounded-xl border border-[var(--beatline-border)] bg-[var(--beatline-surface)]/65 p-4 text-left transition-all duration-300 hover:-translate-y-0.5 hover:border-[var(--beatline-gold-dark)] hover:bg-[color:var(--beatline-highlight)]"
              key={deck.title}
              type="button"
            >
              <p className="text-lg font-semibold text-[var(--beatline-text)] transition-colors group-hover:text-[var(--beatline-gold)]">
                {deck.title}
              </p>
              <p className="mt-1 text-sm text-[var(--beatline-muted)]">
                {deck.cards}
              </p>
            </button>
          ))}
        </section>

        <footer className="mx-auto mt-14 flex flex-wrap items-center justify-center gap-8 text-sm text-[var(--beatline-muted)]">
          <button
            className="transition-colors hover:text-[var(--beatline-gold)]"
            type="button"
          >
            Vorhandenes Deck öffnen
          </button>
          <button
            className="transition-colors hover:text-[var(--beatline-gold)]"
            type="button"
          >
            Aus Spotify-Playlist importieren
          </button>
        </footer>
      </main>
    </div>
  );
};
