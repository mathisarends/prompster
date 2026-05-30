import { useState } from "react";
import { ArrowRight, Check } from "lucide-react";

import { Chip } from "@/components/shared/ui/chip";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import type { PendingInput } from "@/pages/chat-page.state";

type OnboardingPanelProps = {
  pendingInput: PendingInput;
  isSubmitting: boolean;
  onSubmit: (answer: string) => void;
  className?: string;
};

export const OnboardingPanel = ({
  pendingInput,
  isSubmitting,
  onSubmit,
  className,
}: OnboardingPanelProps) => {
  const question = pendingInput.question?.trim();
  const options = pendingInput.options ?? [];
  const isLastQuestion = Boolean(pendingInput.isLastQuestion);

  // The caller remounts this panel per question (keyed by questionId), so the
  // local selection always starts fresh when a new question streams in.
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [freeText, setFreeText] = useState("");

  const answer = (freeText.trim() || selectedOption?.trim()) ?? "";
  const canSubmit = answer.length > 0 && !isSubmitting;

  const handleSelectOption = (option: string) => {
    setSelectedOption((current) => (current === option ? null : option));
    setFreeText("");
  };

  const handleSubmit = () => {
    if (!canSubmit) return;
    onSubmit(answer);
  };

  return (
    <section
      className={cn(
        "flex h-full min-h-0 flex-col bg-[hsl(222_36%_7%)] text-foreground",
        className,
      )}
    >
      <div className="flex min-h-0 flex-1 flex-col gap-7 overflow-y-auto px-7 py-9">
        <div className="space-y-2.5">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
            {isLastQuestion ? "Letzte Frage" : "Kurz zum Einstieg"}
          </p>
          <h2 className="text-balance text-2xl font-medium leading-snug text-foreground">
            {question || "Erzähl mir etwas mehr über deine Playlist."}
          </h2>
        </div>

        {options.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {options.map((option) => {
              const active = selectedOption === option;
              return (
                <Chip
                  key={option}
                  label={option}
                  icon={active ? Check : undefined}
                  active={active}
                  disabled={isSubmitting}
                  onClick={() => handleSelectOption(option)}
                />
              );
            })}
          </div>
        ) : null}

        <div className="space-y-2">
          <label
            htmlFor="onboarding-free-text"
            className="text-sm text-muted-foreground"
          >
            {options.length > 0
              ? "Oder formuliere es in eigenen Worten"
              : "Deine Antwort"}
          </label>
          <Textarea
            id="onboarding-free-text"
            value={freeText}
            onChange={(event) => {
              setFreeText(event.target.value);
              if (event.target.value) setSelectedOption(null);
            }}
            placeholder="Freitext ..."
            rows={3}
            disabled={isSubmitting}
            className="resize-none border-border/60 bg-card/40"
          />
        </div>
      </div>

      <div className="flex shrink-0 items-center justify-end border-t border-white/[0.06] px-7 py-4">
        <Button type="button" onClick={handleSubmit} disabled={!canSubmit}>
          {isLastQuestion ? "Abschließen" : "Weiter"}
          <ArrowRight className="size-4" />
        </Button>
      </div>
    </section>
  );
};
