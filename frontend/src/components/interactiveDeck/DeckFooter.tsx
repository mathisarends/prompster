import { useNavigate } from "react-router-dom";
import { Button } from "../Button";

type DeckFooterProps = {
  onExport?: () => void;
};

export const DeckFooter = ({ onExport }: DeckFooterProps) => {
  const navigate = useNavigate();

  return (
    <div className="border-t border-[var(--beatline-border)] p-4">
      <div className="flex flex-wrap items-center justify-end gap-3">
        <Button
          variant="ghost"
          className="rounded-md border border-[var(--beatline-border)] px-4 py-2 text-sm font-medium text-[var(--beatline-muted)] hover:border-[var(--beatline-gold-dark)]"
          onClick={() => navigate("/")}
        >
          Zuruck zur Startseite
        </Button>
        <Button onClick={onExport}>Karten exportieren -&gt;</Button>
      </div>
    </div>
  );
};
