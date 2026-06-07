import { useMemo, useState } from "react";
import { ArrowLeft, ArrowRight, Check, ListChecks } from "lucide-react";

import { Chip } from "@/shared/ui/chip";
import { Button } from "@/shared/ui/button";
import { cn } from "@/shared/lib/utils";
import type {
  PendingInput,
  PendingOnboardingQuestion,
} from "@/features/chat/state/chat-reducer";

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
  onAnswerChange?: (answer: OnboardingAnswer) => void;
  onSubmit: (answers: OnboardingAnswer[]) => void;
  className?: string;
};

type AnswerDraft = {
  selectedOptions: string[];
  freeText: string;
};

const QUESTIONS_PER_STEP = 3;

const getQuestionAnswers = (draft: AnswerDraft | undefined) => {
  const freeText = draft?.freeText.trim();
  if (freeText) return [freeText];
  return (draft?.selectedOptions ?? [])
    .map((option) => option.trim())
    .filter(Boolean);
};

// Restore previously persisted answers so a refresh mid-onboarding keeps the
// user's selection. Answers that aren't part of the offered options are treated
// as free text, mirroring how the draft is read back in getQuestionAnswers.
const buildInitialDrafts = (
  questions: PendingOnboardingQuestion[],
): Record<string, AnswerDraft> => {
  const drafts: Record<string, AnswerDraft> = {};
  for (const question of questions) {
    if (!question.id || question.answers.length === 0) continue;

    const options = question.options ?? [];
    const freeTextAnswers = question.answers.filter(
      (answer) => !options.includes(answer),
    );

    drafts[question.id] = freeTextAnswers.length
      ? { selectedOptions: [], freeText: freeTextAnswers.join(", ") }
      : { selectedOptions: question.answers, freeText: "" };
  }
  return drafts;
};

const isOtherOption = (option: string) =>
  /^(other|other\.{1,3}|andere|sonstiges)$/i.test(option.trim());

const isExclusiveOption = (option: string) =>
  /(entscheide für mich|decide for me|egal|überrasch)/i.test(option.trim());

const getNextSelectedOptions = (
  question: PendingOnboardingQuestion,
  selectedOptions: string[],
  option: string,
) => {
  if (question.selectionMode !== "multi_select") {
    return selectedOptions[0] === option ? [] : [option];
  }

  if (selectedOptions.includes(option)) {
    return selectedOptions.filter((selected) => selected !== option);
  }

  if (isExclusiveOption(option)) {
    return [option];
  }

  return [
    ...selectedOptions.filter((selected) => !isExclusiveOption(selected)),
    option,
  ];
};

const chunk = <T,>(items: T[], size: number): T[][] => {
  const groups: T[][] = [];
  for (let index = 0; index < items.length; index += size) {
    groups.push(items.slice(index, index + size));
  }
  return groups;
};

export const OnboardingPanel = ({
  pendingInput,
  isSubmitting,
  onAnswerChange,
  onSubmit,
  className,
}: OnboardingPanelProps) => {
  const questions = useMemo(
    () =>
      pendingInput.questions.length
        ? pendingInput.questions
        : [
            {
              id: pendingInput.questionId ?? "",
              question: pendingInput.question ?? null,
              hint: pendingInput.hint ?? null,
              options: pendingInput.options ?? [],
              selectionMode: pendingInput.selectionMode ?? "single_select",
              isLastQuestion: Boolean(pendingInput.isLastQuestion),
              answers: [],
              isAnswered: false,
            },
          ],
    [
      pendingInput.isLastQuestion,
      pendingInput.hint,
      pendingInput.options,
      pendingInput.question,
      pendingInput.questionId,
      pendingInput.questions,
      pendingInput.selectionMode,
    ],
  );
  const [drafts, setDrafts] = useState<Record<string, AnswerDraft>>(() =>
    buildInitialDrafts(questions),
  );
  const [stepIndex, setStepIndex] = useState(0);

  const steps = useMemo(
    () => chunk(questions, QUESTIONS_PER_STEP),
    [questions],
  );
  const currentStep = Math.min(stepIndex, steps.length - 1);
  const stepQuestions = steps[currentStep] ?? [];
  const isLastStep = currentStep === steps.length - 1;
  const firstQuestionNumber = currentStep * QUESTIONS_PER_STEP + 1;

  const answers = useMemo(
    () =>
      questions
        .map((question) => ({
          questionId: question.id,
          answers: getQuestionAnswers(drafts[question.id]),
          answer: getQuestionAnswers(drafts[question.id]).join(", "),
          isLastQuestion: question.isLastQuestion,
        }))
        .filter((answer) => answer.questionId && answer.answers.length > 0),
    [questions, drafts],
  );

  const stepAnswered = stepQuestions.every(
    (question) => getQuestionAnswers(drafts[question.id]).length > 0,
  );
  const allAnswered = answers.length === questions.length;
  const canGoNext = stepAnswered && !isSubmitting;
  const canSubmit = allAnswered && !isSubmitting;

  const handleSelectOption = (
    question: PendingOnboardingQuestion,
    option: string,
  ) => {
    const currentDraft = drafts[question.id] ?? {
      selectedOptions: [],
      freeText: "",
    };
    const nextDraft = {
      selectedOptions: getNextSelectedOptions(
        question,
        currentDraft.selectedOptions,
        option,
      ),
      freeText: "",
    };

    setDrafts((current) => {
      return {
        ...current,
        [question.id]: nextDraft,
      };
    });

    const nextAnswers = getQuestionAnswers(nextDraft);
    if (nextAnswers.length === 0) return;

    onAnswerChange?.({
      questionId: question.id,
      answer: nextAnswers.join(", "),
      answers: nextAnswers,
      isLastQuestion: question.isLastQuestion,
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

  const handleBack = () => {
    setStepIndex((index) => Math.max(0, index - 1));
  };

  const handleNext = () => {
    if (isLastStep) {
      if (canSubmit) onSubmit(answers);
      return;
    }
    if (canGoNext) setStepIndex((index) => index + 1);
  };

  return (
    <section
      className={cn(
        "flex h-full min-h-0 flex-col bg-[#070b0c] text-foreground",
        className,
      )}
    >
      <div className="shrink-0 space-y-4 px-7 pt-9">
        <div className="flex items-center justify-between gap-4">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
            Einleitende Fragen
          </p>
          <p className="text-xs font-medium tabular-nums text-muted-foreground">
            Schritt {currentStep + 1} / {steps.length}
          </p>
        </div>

        <div className="flex gap-1.5" aria-hidden>
          {steps.map((group, index) => {
            const groupAnswered = group.every(
              (question) => getQuestionAnswers(drafts[question.id]).length > 0,
            );
            const isCurrent = index === currentStep;
            return (
              <span
                key={index}
                className={cn(
                  "h-1 flex-1 rounded-full transition-colors",
                  index < currentStep || groupAnswered
                    ? "bg-primary/70"
                    : "bg-white/10",
                  isCurrent && "bg-primary",
                )}
              />
            );
          })}
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-7 py-10">
        <div
          key={currentStep}
          className="m-auto flex w-full max-w-3xl flex-col gap-8 animate-in fade-in slide-in-from-bottom-1 duration-300"
        >
          <div className="flex flex-col gap-12">
            {stepQuestions.map((question, index) => (
              <OnboardingQuestionBlock
                key={question.id || index}
                question={question}
                number={firstQuestionNumber + index}
                draft={drafts[question.id]}
                disabled={isSubmitting}
                onSelectOption={handleSelectOption}
                onFreeTextChange={handleFreeTextChange}
              />
            ))}
          </div>
        </div>
      </div>

      <div className="flex shrink-0 items-center justify-between gap-3 border-t border-white/[0.06] px-7 py-4">
        <Button
          type="button"
          variant="ghost"
          onClick={handleBack}
          disabled={currentStep === 0 || isSubmitting}
          className={cn(currentStep === 0 && "invisible")}
        >
          <ArrowLeft className="size-4" />
          Zurück
        </Button>
        <Button
          type="button"
          onClick={handleNext}
          disabled={isLastStep ? !canSubmit : !canGoNext}
        >
          {isLastStep ? "Abschließen" : "Weiter"}
          <ArrowRight className="size-4" />
        </Button>
      </div>
    </section>
  );
};

type OnboardingQuestionBlockProps = {
  question: PendingOnboardingQuestion;
  number: number;
  draft: AnswerDraft | undefined;
  disabled: boolean;
  onSelectOption: (question: PendingOnboardingQuestion, option: string) => void;
  onFreeTextChange: (questionId: string, value: string) => void;
};

const OnboardingQuestionBlock = ({
  question,
  number,
  draft,
  disabled,
  onSelectOption,
  onFreeTextChange,
}: OnboardingQuestionBlockProps) => {
  const options = (question.options ?? []).filter(
    (option) => !isOtherOption(option),
  );
  const freeTextId = `onboarding-free-text-${question.id || number}`;
  const isMultiSelect = question.selectionMode === "multi_select";

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <div className="flex items-center gap-2.5">
          <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-primary/15 text-[11px] font-semibold text-primary">
            {number}
          </span>
          <h3 className="text-balance text-base font-medium leading-snug text-foreground/90">
            {question.question || "Erzähl mir etwas mehr über deine Playlist."}
          </h3>
        </div>
        {isMultiSelect ? (
          <p className="flex items-center gap-1.5 pl-[1.875rem] text-xs font-medium text-primary/80">
            <ListChecks className="size-3.5 shrink-0" />
            Mehrfachauswahl möglich
          </p>
        ) : null}
      </div>

      {question.hint ? (
        <p className="pl-[0.5rem] text-sm leading-relaxed text-muted-foreground">
          {question.hint}
        </p>
      ) : null}

      <div className="flex max-w-3xl flex-wrap gap-2.5">
        {options.map((option) => {
          const active = draft?.selectedOptions.includes(option) ?? false;
          return (
            <Chip
              key={option}
              label={option}
              icon={active ? Check : undefined}
              active={active}
              activeClassName="border-primary/50 bg-primary/15 text-foreground shadow-[0_2px_16px_-6px_hsl(141_73%_42%/0.5)] [&>svg]:text-primary hover:border-primary/60 hover:bg-primary/20 hover:text-foreground"
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
        active &&
          "border-primary/50 bg-primary/15 text-foreground shadow-[0_2px_16px_-6px_hsl(141_73%_42%/0.5)]",
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
