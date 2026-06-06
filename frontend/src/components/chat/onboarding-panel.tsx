import { useState } from "react";
import { ArrowRight, Check } from "lucide-react";

import { Chip } from "@/components/shared/ui/chip";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type {
  PendingInput,
  PendingOnboardingQuestion,
} from "@/pages/chat-page.state";

export type OnboardingAnswer = {
  questionId: string;
  answer: string;
  answers: string[];
  isLastQuestion: boolean;
};

type OnboardingPanelProps = {
  pendingInput: PendingInput;
  deckTitle?: string;
  isSubmitting: boolean;
  onSubmit: (answers: OnboardingAnswer[]) => void;
  className?: string;
};

type AnswerDraft = {
  selectedOptions: string[];
  freeText: string;
};

const getQuestionAnswers = (draft: AnswerDraft | undefined) => {
  const freeText = draft?.freeText.trim();
  if (freeText) return [freeText];
  return (draft?.selectedOptions ?? [])
    .map((option) => option.trim())
    .filter(Boolean);
};

const isOtherOption = (option: string) =>
  /^(other|other\.{1,3}|andere|sonstiges)$/i.test(option.trim());

export const OnboardingPanel = ({
  pendingInput,
  deckTitle,
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
          selectionMode: pendingInput.selectionMode ?? "single_select",
          isLastQuestion: Boolean(pendingInput.isLastQuestion),
        },
      ];
  const isLastQuestion = questions.some((question) => question.isLastQuestion);
  const [drafts, setDrafts] = useState<Record<string, AnswerDraft>>({});

  const answers = questions
    .map((question) => ({
      questionId: question.id,
      answers: getQuestionAnswers(drafts[question.id]),
      answer: getQuestionAnswers(drafts[question.id]).join(", "),
      isLastQuestion: question.isLastQuestion,
    }))
    .filter((answer) => answer.questionId && answer.answers.length > 0);
  const canSubmit = answers.length === questions.length && !isSubmitting;

  const handleSelectOption = (question: PendingOnboardingQuestion, option: string) => {
    setDrafts((current) => {
      const draft = current[question.id] ?? {
        selectedOptions: [],
        freeText: "",
      };
      const selectedOptions =
        question.selectionMode === "multi_select"
          ? draft.selectedOptions.includes(option)
            ? draft.selectedOptions.filter((selected) => selected !== option)
            : [...draft.selectedOptions, option]
          : draft.selectedOptions[0] === option
            ? []
            : [option];
      return {
        ...current,
        [question.id]: {
          selectedOptions,
          freeText: "",
        },
      };
    });
  };

  const handleFreeTextChange = (questionId: string, value: string) => {
    setDrafts((current) => ({
      ...current,
      [questionId]: {
        selectedOptions: value
          ? []
          : (current[questionId]?.selectedOptions ?? []),
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
      <div className="flex min-h-0 flex-1 flex-col gap-8 overflow-y-auto px-7 py-9">
        <div className="space-y-2">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
            Onboarding
          </p>
          <h2 className="text-balance text-2xl font-medium leading-snug text-foreground">
            {deckTitle
              ? `Ein paar Fragen zum Deck „${deckTitle}“`
              : "Ein paar Fragen zu deinem Deck"}
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
  onSelectOption: (question: PendingOnboardingQuestion, option: string) => void;
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
  const options = (question.options ?? []).filter(
    (option) => !isOtherOption(option),
  );
  const freeTextId = `onboarding-free-text-${question.id || index}`;

  return (
    <div
      className={cn(
        "space-y-4",
        showDivider && "border-t border-white/[0.06] pt-8",
      )}
    >
      <h3 className="text-balance text-base font-medium leading-snug text-foreground/90">
        {question.question || "Erzähl mir etwas mehr über deine Playlist."}
      </h3>

      <div className="flex flex-wrap gap-2">
        {options.map((option) => {
          const active = draft?.selectedOptions.includes(option) ?? false;
          return (
            <Chip
              key={option}
              label={option}
              icon={active ? Check : undefined}
              active={active}
              activeClassName="border-primary/45 bg-primary/15 text-foreground [&>svg]:text-primary hover:border-primary/55 hover:bg-primary/20 hover:text-foreground"
              disabled={disabled}
              onClick={() => onSelectOption(question, option)}
            />
          );
        })}
        <WritableAnswerChip
          id={freeTextId}
          value={draft?.freeText ?? ""}
          disabled={disabled}
          hasOptions={options.length > 0}
          onChange={(value) => onFreeTextChange(question.id, value)}
        />
      </div>
    </div>
  );
};

type WritableAnswerChipProps = {
  id: string;
  value: string;
  disabled: boolean;
  hasOptions: boolean;
  onChange: (value: string) => void;
};

const WritableAnswerChip = ({
  id,
  value,
  disabled,
  hasOptions,
  onChange,
}: WritableAnswerChipProps) => {
  const active = value.trim().length > 0;

  return (
    <label
      htmlFor={id}
      className={cn(
        "flex h-10 min-w-36 max-w-full items-center rounded-full border border-border/60 bg-card/40 px-4 text-sm text-muted-foreground backdrop-blur-sm transition-colors focus-within:border-primary/60 focus-within:bg-primary/10 focus-within:text-foreground",
        active && "border-primary/45 bg-primary/15 text-foreground",
        disabled && "pointer-events-none opacity-50",
      )}
    >
      <input
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={hasOptions ? "Other..." : "Antwort..."}
        disabled={disabled}
        className="h-full min-w-0 flex-1 bg-transparent text-sm text-inherit outline-none placeholder:text-muted-foreground"
      />
    </label>
  );
};
