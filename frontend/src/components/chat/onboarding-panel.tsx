import { useState } from "react";
import { ArrowRight, Check } from "lucide-react";

import { Chip } from "@/components/shared/ui/chip";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import type {
  PendingInput,
  PendingOnboardingQuestion,
} from "@/pages/chat-page.state";

export type OnboardingAnswer = {
  questionId: string;
  answer: string;
  isLastQuestion: boolean;
};

type OnboardingPanelProps = {
  pendingInput: PendingInput;
  isSubmitting: boolean;
  onSubmit: (answers: OnboardingAnswer[]) => void;
  className?: string;
};

type AnswerDraft = {
  selectedOption: string | null;
  freeText: string;
};

const getQuestionAnswer = (draft: AnswerDraft | undefined) =>
  (draft?.freeText.trim() || draft?.selectedOption?.trim()) ?? "";

export const OnboardingPanel = ({
  pendingInput,
  isSubmitting,
  onSubmit,
  className,
}: OnboardingPanelProps) => {
  const questions = pendingInput.questions.length
    ? pendingInput.questions
    : [
        {
          id: pendingInput.questionId ?? "",
          question: pendingInput.question ?? null,
          options: pendingInput.options ?? [],
          isLastQuestion: Boolean(pendingInput.isLastQuestion),
        },
      ];
  const isLastQuestion = questions.some((question) => question.isLastQuestion);
  const [drafts, setDrafts] = useState<Record<string, AnswerDraft>>({});

  const answers = questions
    .map((question) => ({
      questionId: question.id,
      answer: getQuestionAnswer(drafts[question.id]),
      isLastQuestion: question.isLastQuestion,
    }))
    .filter((answer) => answer.questionId && answer.answer.length > 0);
  const canSubmit = answers.length === questions.length && !isSubmitting;

  const handleSelectOption = (questionId: string, option: string) => {
    setDrafts((current) => {
      const draft = current[questionId] ?? {
        selectedOption: null,
        freeText: "",
      };
      return {
        ...current,
        [questionId]: {
          selectedOption: draft.selectedOption === option ? null : option,
          freeText: "",
        },
      };
    });
  };

  const handleFreeTextChange = (questionId: string, value: string) => {
    setDrafts((current) => ({
      ...current,
      [questionId]: {
        selectedOption: value
          ? null
          : (current[questionId]?.selectedOption ?? null),
        freeText: value,
      },
    }));
  };

  const handleSubmit = () => {
    if (!canSubmit) return;
    onSubmit(answers);
  };

  return (
    <section
      className={cn(
        "flex h-full min-h-0 flex-col bg-[hsl(222_36%_7%)] text-foreground",
        className,
      )}
    >
      <div className="flex min-h-0 flex-1 flex-col gap-7 overflow-y-auto px-7 py-9">
        <div className="space-y-2">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
            {isLastQuestion ? "Letzte Frage" : "Kurz zum Einstieg"}
          </p>
          <h2 className="text-balance text-2xl font-medium leading-snug text-foreground">
            Kurz zum Einstieg
          </h2>
        </div>

        <div className="flex flex-col gap-8">
          {questions.map((question, index) => (
            <OnboardingQuestionBlock
              key={question.id || index}
              question={question}
              index={index}
              draft={drafts[question.id]}
              disabled={isSubmitting}
              showDivider={index > 0}
              onSelectOption={handleSelectOption}
              onFreeTextChange={handleFreeTextChange}
            />
          ))}
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

type OnboardingQuestionBlockProps = {
  question: PendingOnboardingQuestion;
  index: number;
  draft: AnswerDraft | undefined;
  disabled: boolean;
  showDivider: boolean;
  onSelectOption: (questionId: string, option: string) => void;
  onFreeTextChange: (questionId: string, value: string) => void;
};

const OnboardingQuestionBlock = ({
  question,
  index,
  draft,
  disabled,
  showDivider,
  onSelectOption,
  onFreeTextChange,
}: OnboardingQuestionBlockProps) => {
  const options = question.options ?? [];
  const freeTextId = `onboarding-free-text-${question.id || index}`;

  return (
    <div
      className={cn(
        "space-y-5",
        showDivider && "border-t border-white/[0.06] pt-8",
      )}
    >
      <div className="space-y-2">
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-primary/80">
          Frage {question.sequenceNumber ?? index + 1}
        </p>
        <h3 className="text-balance text-xl font-medium leading-snug text-foreground">
          {question.question || "Erzähl mir etwas mehr über deine Playlist."}
        </h3>
      </div>

      {options.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {options.map((option) => {
            const active = draft?.selectedOption === option;
            return (
              <Chip
                key={option}
                label={option}
                icon={active ? Check : undefined}
                active={active}
                activeClassName="border-primary/55 bg-primary/15 text-primary shadow-[0_0_0_1px_hsl(141_73%_42%/0.12)] hover:border-primary/70 hover:bg-primary/20 hover:text-primary"
                disabled={disabled}
                onClick={() => onSelectOption(question.id, option)}
              />
            );
          })}
        </div>
      ) : null}

      <div className="space-y-2">
        <label htmlFor={freeTextId} className="text-sm text-muted-foreground">
          {options.length > 0
            ? "Oder formuliere es in eigenen Worten"
            : "Deine Antwort"}
        </label>
        <Textarea
          id={freeTextId}
          value={draft?.freeText ?? ""}
          onChange={(event) => onFreeTextChange(question.id, event.target.value)}
          placeholder="Freitext ..."
          rows={3}
          disabled={disabled}
          className="resize-none border-border/60 bg-card/40"
        />
      </div>
    </div>
  );
};
