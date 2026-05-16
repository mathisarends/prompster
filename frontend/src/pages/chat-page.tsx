import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { Sparkles } from "lucide-react";

import { ChatInputBox } from "@/components/chat-input-box";
import {
  FollowUpQuestionCard,
  type FollowUpQuestionOption,
} from "@/components/follow-up-question-card";

type ChatRole = "assistant" | "user";

type ChatMessage = {
  id: string;
  role: ChatRole;
  text: string;
};

type FollowUpStepConfig = {
  id: string;
  question: string;
  options: FollowUpQuestionOption[];
};

const followUpSteps: FollowUpStepConfig[] = [
  {
    id: "category",
    question: "Was steht heute an?",
    options: [
      { id: "work", label: "Vizro / Arbeit" },
      { id: "university", label: "Uni-Aufgabe" },
      { id: "open-source", label: "Open-Source-Projekt" },
      { id: "other", label: "Etwas anderes" },
    ],
  },
  {
    id: "project",
    question: "Welches Open-Source-Projekt?",
    options: [
      { id: "notionary", label: "notionary" },
      { id: "rtvoice", label: "rtvoice" },
      { id: "agentory", label: "agentory" },
      { id: "hueify", label: "hueify / cdpify / anderes" },
    ],
  },
  {
    id: "output",
    question: "Welches Format brauchst du?",
    options: [
      { id: "deck", label: "Karten-Deck" },
      { id: "summary", label: "Zusammenfassung" },
      { id: "outline", label: "Outline" },
      { id: "draft", label: "Erstentwurf" },
    ],
  },
];

const createFirstFollowUpMessage = (): ChatMessage => ({
  id: `assistant-${crypto.randomUUID()}`,
  role: "assistant",
  text: "Verstanden. Ich brauche noch kurz Kontext, damit ich die nächsten Rückfragen passend stellen kann.",
});

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
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    if (!initialPrompt) return [];

    return [
      {
        id: `user-${crypto.randomUUID()}`,
        role: "user",
        text: initialPrompt,
      },
      createFirstFollowUpMessage(),
    ];
  });
  const [showFollowUp, setShowFollowUp] = useState(
    () => initialPrompt !== undefined,
  );
  const [followUpStepIndex, setFollowUpStepIndex] = useState(0);
  const [stepAnswers, setStepAnswers] = useState<Record<string, string>>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const sendMessage = useCallback(
    (text: string) => {
      const shouldAskFollowUp = messages.length === 0;

      setMessages((currentMessages) => {
        const userMessage: ChatMessage = {
          id: `user-${crypto.randomUUID()}`,
          role: "user",
          text,
        };

        const assistantMessage: ChatMessage = {
          id: `assistant-${crypto.randomUUID()}`,
          role: "assistant",
          text:
            currentMessages.length === 0
              ? createFirstFollowUpMessage().text
              : "Alles klar. Ich nehme das mit auf und verfeinere den Deck-Plan weiter.",
        };

        return [...currentMessages, userMessage, assistantMessage];
      });

      if (shouldAskFollowUp) {
        setShowFollowUp(true);
        setFollowUpStepIndex(0);
        setStepAnswers({});
      }
    },
    [messages.length],
  );

  const finalizeFollowUp = useCallback((answers: Record<string, string>) => {
    const summary = followUpSteps
      .map((step) => answers[step.id])
      .filter(Boolean)
      .join(" · ");

    setMessages((currentMessages) => [
      ...currentMessages,
      {
        id: `user-${crypto.randomUUID()}`,
        role: "user",
        text: summary || "(keine Auswahl)",
      },
      {
        id: `assistant-${crypto.randomUUID()}`,
        role: "assistant",
        text: "Danke, ich nehme die Einordnung mit und gehe an den Plan.",
      },
    ]);
    setShowFollowUp(false);
    setFollowUpStepIndex(0);
    setStepAnswers({});
  }, []);

  const answerFollowUp = useCallback(
    (answer: string, _option?: FollowUpQuestionOption) => {
      const currentStep = followUpSteps[followUpStepIndex];
      if (!currentStep) return;

      const nextAnswers = { ...stepAnswers, [currentStep.id]: answer };
      setStepAnswers(nextAnswers);

      if (followUpStepIndex < followUpSteps.length - 1) {
        setFollowUpStepIndex(followUpStepIndex + 1);
        return;
      }

      finalizeFollowUp(nextAnswers);
    },
    [finalizeFollowUp, followUpStepIndex, stepAnswers],
  );

  const skipFollowUp = useCallback(() => {
    setMessages((currentMessages) => [
      ...currentMessages,
      {
        id: `assistant-${crypto.randomUUID()}`,
        role: "assistant",
        text: "Alles klar, ich mache ohne diese Einordnung weiter.",
      },
    ]);
    setShowFollowUp(false);
    setFollowUpStepIndex(0);
    setStepAnswers({});
  }, []);

  const dismissFollowUp = useCallback(() => {
    setShowFollowUp(false);
    setFollowUpStepIndex(0);
    setStepAnswers({});
  }, []);

  const goToPrevStep = useCallback(() => {
    setFollowUpStepIndex((index) => Math.max(0, index - 1));
  }, []);

  const goToNextStep = useCallback(() => {
    setFollowUpStepIndex((index) =>
      Math.min(followUpSteps.length - 1, index + 1),
    );
  }, []);

  useEffect(() => {
    if (messages.length === 0) return;
    messagesEndRef.current?.scrollIntoView({ block: "end" });
  }, [messages]);

  const renderMessage = (message: ChatMessage) => {
    if (message.role === "user") {
      return (
        <div
          key={message.id}
          className="ml-auto max-w-[82%] rounded-2xl bg-white/10 px-4 py-3 text-sm leading-relaxed text-foreground sm:text-base"
        >
          {message.text}
        </div>
      );
    }

    return (
      <div
        key={message.id}
        className="flex max-w-[82%] flex-col gap-1.5 px-1 py-2"
      >
        <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-foreground/80">
          Prompster
        </span>
        <div className="text-sm leading-relaxed text-muted-foreground sm:text-base">
          {message.text}
        </div>
      </div>
    );
  };

  const currentStep = followUpSteps[followUpStepIndex];
  const isFirstStep = followUpStepIndex === 0;
  const isLastStep = followUpStepIndex === followUpSteps.length - 1;

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
            {messages.map(renderMessage)}
            <div ref={messagesEndRef} />
          </div>
        </div>
      </main>

      <div className="sticky bottom-0 z-10 bg-gradient-to-t from-background via-background/85 to-transparent px-4 pb-4 pt-6 sm:px-8 sm:pb-3">
        <div className="mx-auto w-full max-w-4xl">
          {showFollowUp && currentStep && (
            <div className="mb-3">
              <FollowUpQuestionCard
                key={currentStep.id}
                question={currentStep.question}
                options={currentStep.options}
                onAnswer={answerFollowUp}
                onSkip={skipFollowUp}
                onDismiss={dismissFollowUp}
                step={{
                  current: followUpStepIndex + 1,
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
