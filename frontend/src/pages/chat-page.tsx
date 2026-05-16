import { useCallback, useReducer, useState } from "react";
import { useLocation } from "react-router-dom";
import { Sparkles } from "lucide-react";

import { AssistantChatMessage } from "@/components/assistant-chat-message";
import { ChatInputBox } from "@/components/chat-input-box";
import { FollowUpQuestionFlow } from "@/components/follow-up-question-flow";
import { UserChatMessage } from "@/components/user-chat-message";
import { useAutoScrollToBottom } from "@/hooks/useAutoScrollToBottom";

import {
  chatReducer,
  createInitialChatState,
  followUpSteps,
} from "./chat-page.state";

const getInitialPrompt = (state: unknown) => {
  if (!state || typeof state !== "object" || !("initialPrompt" in state)) {
    return undefined;
  }

  const initialPrompt = (state as { initialPrompt?: unknown }).initialPrompt;
  if (typeof initialPrompt !== "string") return undefined;

  const trimmedPrompt = initialPrompt.trim();
  return trimmedPrompt.length > 0 ? trimmedPrompt : undefined;
};

export const ChatPage = () => {
  const location = useLocation();
  const initialPrompt = getInitialPrompt(location.state);
  const [prompt, setPrompt] = useState("");
  const [state, dispatch] = useReducer(
    chatReducer,
    initialPrompt,
    createInitialChatState,
  );
  const { messages, followUp } = state;
  const messagesEndRef = useAutoScrollToBottom<HTMLDivElement>(messages.length);

  const sendMessage = useCallback(
    (text: string) => dispatch({ type: "send-message", text }),
    [],
  );
  const answerFollowUp = useCallback(
    (answer: string) => dispatch({ type: "answer-follow-up", answer }),
    [],
  );
  const skipFollowUp = useCallback(
    () => dispatch({ type: "skip-follow-up" }),
    [],
  );
  const dismissFollowUp = useCallback(
    () => dispatch({ type: "dismiss-follow-up" }),
    [],
  );
  const goToPrevStep = useCallback(
    () => dispatch({ type: "go-to-prev-step" }),
    [],
  );
  const goToNextStep = useCallback(
    () => dispatch({ type: "go-to-next-step" }),
    [],
  );

  const isFollowUpActive = followUp.status === "active";
  const currentStepIndex = isFollowUpActive ? followUp.stepIndex : 0;
  const currentStep = isFollowUpActive
    ? followUpSteps[currentStepIndex]
    : undefined;
  const isFirstStep = currentStepIndex === 0;
  const isLastStep = currentStepIndex === followUpSteps.length - 1;

  return (
    <div className="chat-page-background flex min-h-dvh flex-col text-foreground">
      <header className="fixed inset-x-0 top-0 z-20 flex h-14 px-20 items-center justify-start bg-background/80 backdrop-blur-md">
        <span className="inline-flex items-center gap-2.5 text-sm font-semibold text-foreground/85">
          <Sparkles className="size-3.5" />
          Neues Karten-Deck
        </span>
      </header>

      <main className="relative z-10 flex flex-1 flex-col px-4 pt-14 sm:px-8">
        <div className="mx-auto flex w-full max-w-4xl flex-col">
          <div className="flex flex-col gap-4 px-1 pt-1 sm:px-2">
            {messages.map((message) =>
              message.role === "user" ? (
                <UserChatMessage key={message.id} text={message.text} />
              ) : (
                <AssistantChatMessage key={message.id} text={message.text} />
              ),
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>
      </main>

      <div className="sticky bottom-0 z-10 bg-gradient-to-t from-background via-background/85 to-transparent px-4 pb-4 pt-6 sm:px-8 sm:pb-3">
        <div className="mx-auto w-full max-w-4xl">
          {currentStep && (
            <div className="mb-3">
              <FollowUpQuestionFlow
                key={currentStep.id}
                question={currentStep.question}
                options={currentStep.options}
                onAnswer={answerFollowUp}
                onSkip={skipFollowUp}
                onDismiss={dismissFollowUp}
                step={{
                  current: currentStepIndex + 1,
                  total: followUpSteps.length,
                  onPrev: isFirstStep ? undefined : goToPrevStep,
                  onNext: isLastStep ? undefined : goToNextStep,
                }}
                className="rounded-3xl border-border/60 bg-card/90"
              />
            </div>
          )}
          <ChatInputBox
            value={prompt}
            onChange={setPrompt}
            onSubmit={sendMessage}
            disclaimerText="Prompster ist eine KI und kann Fehler machen. Bitte überprüfe die Antworten."
            showDisclaimer
            placeholder="Deine Antwort ..."
            sendButtonAriaLabel="Nachricht senden"
            className="rounded-3xl border border-border/50 bg-card/70 p-4 shadow-2xl shadow-black/20"
            textareaClassName="max-h-40"
            rows={1}
          />
        </div>
      </div>
    </div>
  );
};
