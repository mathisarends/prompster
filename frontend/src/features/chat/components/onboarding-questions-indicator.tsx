import { ListChecks } from "lucide-react";

type OnboardingQuestionsIndicatorProps = {
  count: number;
};

export const OnboardingQuestionsIndicator = ({
  count,
}: OnboardingQuestionsIndicatorProps) => {
  const questionLabel = count === 1 ? "Frage" : "Fragen";

  return (
    <div className="flex max-w-[82%] px-1 py-2" role="status" aria-live="polite">
      <div className="inline-flex items-center gap-3 px-1 py-1 text-sm text-foreground">
        <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-300">
          <ListChecks className="size-4" />
        </span>
        <span className="min-w-0 leading-relaxed">
          <span className="block font-medium">
            Prompster hat {count} {questionLabel} gestellt.
          </span>
          <span className="block text-muted-foreground">
            Beantworte sie im Fragenbereich, damit das Deck gebaut werden kann.
          </span>
        </span>
      </div>
    </div>
  );
};
