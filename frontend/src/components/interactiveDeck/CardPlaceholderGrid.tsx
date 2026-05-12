export const CardPlaceholderGrid = () => {
  return (
    <div className="min-h-0 flex-1 overflow-auto p-4">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
        {Array.from({ length: 6 }).map((_, idx) => (
          <div
            key={`card-placeholder-${idx}`}
            className="rounded-xl border border-[var(--beatline-border)] bg-[var(--beatline-bg)]/70 p-4"
          >
            <div className="mb-3 h-28 rounded-lg border border-[var(--beatline-border)] bg-[var(--beatline-highlight)]/50" />
            <p className="text-sm font-semibold">Kartenansicht Platzhalter</p>
            <p className="mt-1 text-xs text-[var(--beatline-muted)]">
              Hier kommen deine Deck-Karten hin.
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};
