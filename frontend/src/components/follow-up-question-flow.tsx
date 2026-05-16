import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  ChevronLeft,
  ChevronRight,
  CornerDownLeft,
  Pencil,
  X,
} from "lucide-react";

import { SendButton } from "@/components/send-button";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useListKeyboardNavigation } from "@/hooks/useKeyboardShortcut";
import { cn } from "@/lib/utils";

export type FollowUpQuestionOption = {
  id: string;
  label: string;
};

export type FollowUpQuestionStep = {
  current: number;
  total: number;
  onPrev?: () => void;
  onNext?: () => void;
};

type FollowUpQuestionFlowProps = {
  question: string;
  options: FollowUpQuestionOption[];
  value?: string;
  placeholder?: string;
  submitLabel?: string;
  skipLabel?: string;
  className?: string;
  disabled?: boolean;
  autoFocus?: boolean;
  step?: FollowUpQuestionStep;
  onValueChange?: (value: string) => void;
  onAnswer: (answer: string, option?: FollowUpQuestionOption) => void;
  onSkip?: () => void;
  onDismiss?: () => void;
};

export const FollowUpQuestionFlow = ({
  question,
  options,
  value,
  placeholder = "Etwas anderes ...",
  submitLabel = "Antwort senden",
  skipLabel = "Überspringen",
  className,
  disabled = false,
  autoFocus = false,
  step,
  onValueChange,
  onAnswer,
  onSkip,
  onDismiss,
}: FollowUpQuestionFlowProps) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [internalValue, setInternalValue] = useState("");
  const answerValue = value ?? internalValue;
  const trimmedAnswer = answerValue.trim();

  const isLastStep = !step || step.current >= step.total;
  const showStepIndicator = step !== undefined && step.total > 1;

  const setAnswerValue = (nextValue: string) => {
    onValueChange?.(nextValue);

    if (value === undefined) {
      setInternalValue(nextValue);
    }
  };

  const submitFreeAnswer = () => {
    if (!trimmedAnswer || disabled) return;

    onAnswer(trimmedAnswer);
    setAnswerValue("");
  };

  const selectOption = (option: FollowUpQuestionOption) => {
    if (disabled) return;

    onAnswer(option.label, option);
  };

  const { highlightedIndex, setHighlightedIndex } = useListKeyboardNavigation({
    items: options,
    open: !disabled,
    onConfirm: selectOption,
    global: true,
  });

  useEffect(() => {
    if (!autoFocus) return;

    const frameId = requestAnimationFrame(() => {
      textareaRef.current?.focus();
    });

    return () => {
      cancelAnimationFrame(frameId);
    };
  }, [autoFocus]);

  const ActionIcon = isLastStep ? CornerDownLeft : ArrowRight;

  return (
    <section
      className={cn(
        "overflow-hidden rounded-2xl border border-white/10 bg-card/80 text-card-foreground shadow-2xl shadow-black/20 backdrop-blur-xl",
        className,
      )}
      aria-label={question}
    >
      <div className="flex items-start gap-3 px-4 py-3 sm:px-5">
        <p className="min-w-0 flex-1 text-sm font-semibold leading-relaxed text-foreground sm:text-base">
          {question}
        </p>

        {showStepIndicator && (
          <div className="flex shrink-0 items-center gap-0.5 text-xs text-muted-foreground">
            <Button
              type="button"
              variant="ghost"
              size="icon-xs"
              onClick={step?.onPrev}
              disabled={disabled || !step?.onPrev || step.current <= 1}
              aria-label="Vorherige Frage"
              className="text-muted-foreground hover:bg-white/10 hover:text-foreground"
            >
              <ChevronLeft className="size-3.5" />
            </Button>
            <span className="px-1 tabular-nums">
              {step?.current} von {step?.total}
            </span>
            <Button
              type="button"
              variant="ghost"
              size="icon-xs"
              onClick={step?.onNext}
              disabled={
                disabled ||
                !step?.onNext ||
                (step?.current ?? 0) >= (step?.total ?? 0)
              }
              aria-label="Nächste Frage"
              className="text-muted-foreground hover:bg-white/10 hover:text-foreground"
            >
              <ChevronRight className="size-3.5" />
            </Button>
          </div>
        )}

        {onDismiss && (
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            onClick={onDismiss}
            disabled={disabled}
            aria-label="Rückfrage schließen"
            className="-mr-2 -mt-1 text-muted-foreground hover:bg-white/10 hover:text-foreground"
          >
            <X className="size-4" />
          </Button>
        )}
      </div>

      <div className="divide-y divide-white/10 border-t border-white/10">
        {options.map((option, index) => {
          const isHighlighted = index === highlightedIndex;

          return (
            <button
              key={option.id}
              type="button"
              onClick={() => selectOption(option)}
              onMouseEnter={() => setHighlightedIndex(index)}
              disabled={disabled}
              className={cn(
                "flex w-full items-center gap-3 px-4 py-2.5 text-left transition-colors focus-visible:outline-none disabled:pointer-events-none disabled:opacity-60 sm:px-5",
                isHighlighted && "bg-white/10",
              )}
            >
              <span className="grid size-6 shrink-0 place-items-center rounded-md bg-black/35 text-xs font-semibold text-foreground/80">
                {index + 1}
              </span>
              <span className="min-w-0 flex-1 truncate text-sm leading-snug text-foreground">
                {option.label}
              </span>
              <ActionIcon
                className={cn(
                  "size-4 shrink-0 text-muted-foreground opacity-0 transition-opacity",
                  isHighlighted && "opacity-100",
                )}
              />
            </button>
          );
        })}

        <div className="flex items-center gap-3 px-4 py-2 focus-within:bg-white/5 sm:px-5">
          <Pencil className="size-4 shrink-0 text-muted-foreground" />
          <Textarea
            ref={textareaRef}
            value={answerValue}
            onChange={(event) => setAnswerValue(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                submitFreeAnswer();
              }
            }}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className="max-h-28 min-h-7 flex-1 resize-none border-0 bg-transparent p-0 text-sm leading-7 shadow-none placeholder:text-muted-foreground focus-visible:ring-0 md:text-sm"
          />
          {trimmedAnswer ? (
            <SendButton
              onClick={submitFreeAnswer}
              disabled={disabled}
              ariaLabel={submitLabel}
              size="icon-xs"
            />
          ) : (
            onSkip && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={onSkip}
                disabled={disabled}
                className="h-7 border-white/15 bg-transparent px-3 text-xs hover:bg-white/10"
              >
                {skipLabel}
              </Button>
            )
          )}
        </div>
      </div>
    </section>
  );
};
