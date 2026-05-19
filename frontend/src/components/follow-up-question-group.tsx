import type {
  FollowUpQuestionGroupEntryResponse,
  FollowUpQuestionResponse,
} from "@/api/generated/model";
import {
  FollowUpQuestionFlow,
  type FollowUpQuestionOption,
} from "@/components/follow-up-question-flow";
import { cn } from "@/lib/utils";

type FollowUpQuestionGroupProps = {
  group: Pick<FollowUpQuestionGroupEntryResponse, "id" | "questions">;
  draftValue?: string;
  disabled?: boolean;
  className?: string;
  onDraftChange: (questionId: string, value: string) => void;
  onAnswer: (
    question: FollowUpQuestionResponse,
    answer: string,
    option?: FollowUpQuestionOption,
  ) => void;
  onSkip: () => void;
};

const getAnswerText = (question: FollowUpQuestionResponse) => {
  if (question.state === "skipped") return "Uebersprungen";
  if (question.answerText) return question.answerText;

  const selectedOption = question.options.find(
    (option) => option.id === question.answeredOptionId,
  );
  return selectedOption?.label ?? "Beantwortet";
};

export const FollowUpQuestionGroup = ({
  group,
  draftValue = "",
  disabled = false,
  className,
  onDraftChange,
  onAnswer,
  onSkip,
}: FollowUpQuestionGroupProps) => {
  const currentQuestionIndex = group.questions.findIndex(
    (question) => question.state === "pending",
  );
  const currentQuestion =
    currentQuestionIndex === -1
      ? undefined
      : group.questions[currentQuestionIndex];
  const resolvedQuestions = group.questions.filter(
    (question) => question.state !== "pending",
  );

  if (group.questions.length === 0) return null;

  return (
    <div className={cn("flex max-w-[82%] flex-col gap-2 px-1 py-2", className)}>
      {resolvedQuestions.length > 0 ? (
        <section className="space-y-2" aria-label="Beantwortete Rueckfragen">
          {resolvedQuestions.map((question) => (
            <div
              key={question.id}
              className="rounded-xl border border-white/10 bg-card/50 px-4 py-3 text-sm shadow-lg shadow-black/10"
            >
              <p className="font-medium leading-relaxed text-foreground">
                {question.question}
              </p>
              <p
                className={cn(
                  "mt-1 break-words text-sm leading-6",
                  question.state === "skipped"
                    ? "text-muted-foreground"
                    : "text-primary",
                )}
              >
                {getAnswerText(question)}
              </p>
            </div>
          ))}
        </section>
      ) : null}

      {currentQuestion ? (
        <FollowUpQuestionFlow
          question={currentQuestion.question}
          options={currentQuestion.options}
          value={draftValue}
          onValueChange={(value) => onDraftChange(currentQuestion.id, value)}
          onAnswer={(answer, option) =>
            onAnswer(currentQuestion, answer, option)
          }
          onSkip={onSkip}
          skipLabel="Rest ueberspringen"
          disabled={disabled}
          autoFocus={!disabled}
          step={{
            current: currentQuestionIndex + 1,
            total: group.questions.length,
          }}
        />
      ) : null}
    </div>
  );
};
