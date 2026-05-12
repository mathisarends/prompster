interface TemplateCardProps {
  title: string;
  cards: string;
  onClick?: () => void;
}

export const TemplateCard = ({ title, cards, onClick }: TemplateCardProps) => (
  <button
    className="group rounded-xl border border-[var(--beatline-border)] bg-[var(--beatline-surface)]/65 p-4 text-left transition-all duration-300 hover:-translate-y-0.5 hover:border-[var(--beatline-gold-dark)] hover:bg-[color:var(--beatline-highlight)]"
    type="button"
    onClick={onClick}
  >
    <p className="text-lg font-semibold text-[var(--beatline-text)] transition-colors group-hover:text-[var(--beatline-gold)]">
      {title}
    </p>
    <p className="mt-1 text-sm text-[var(--beatline-muted)]">{cards}</p>
  </button>
);
