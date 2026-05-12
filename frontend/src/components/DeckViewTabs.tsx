import { LayoutGrid, ListMusic } from "lucide-react";

export type DeckViewMode = "playlist" | "cards";

type DeckViewTabsProps = {
  activeView: DeckViewMode;
  onChange: (nextView: DeckViewMode) => void;
  visibleSongs: number;
  totalSongs: number;
};

export const DeckViewTabs = ({
  activeView,
  onChange,
  visibleSongs,
  totalSongs,
}: DeckViewTabsProps) => {
  return (
    <div className="flex items-center justify-between border-b border-[var(--beatline-border)] px-4">
      <div className="flex items-center gap-4">
        <button
          className={`inline-flex items-center gap-1.5 border-b-2 px-1 py-3 text-sm font-semibold transition-colors ${
            activeView === "playlist"
              ? "border-[var(--beatline-text)] text-[var(--beatline-text)]"
              : "border-transparent text-[var(--beatline-muted)] hover:text-[var(--beatline-text)]"
          }`}
          type="button"
          onClick={() => onChange("playlist")}
        >
          <ListMusic size={14} />
          Liste
        </button>
        <button
          className={`inline-flex items-center gap-1.5 border-b-2 px-1 py-3 text-sm font-semibold transition-colors ${
            activeView === "cards"
              ? "border-[var(--beatline-text)] text-[var(--beatline-text)]"
              : "border-transparent text-[var(--beatline-muted)] hover:text-[var(--beatline-text)]"
          }`}
          type="button"
          onClick={() => onChange("cards")}
        >
          <LayoutGrid size={14} />
          Karten
        </button>
      </div>

      <span className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--beatline-muted)]">
        {visibleSongs} / {totalSongs} Songs
      </span>
    </div>
  );
};
