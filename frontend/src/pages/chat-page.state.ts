import type { FollowUpQuestionOption } from "@/components/follow-up-question-flow";

export type ChatRole = "assistant" | "user";

export type ChatMessage = {
  id: string;
  role: ChatRole;
  text: string;
};

export type FollowUpStepConfig = {
  id: string;
  question: string;
  options: FollowUpQuestionOption[];
};

export const followUpSteps: FollowUpStepConfig[] = [
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

const FIRST_FOLLOW_UP_TEXT =
  "Verstanden. Ich brauche noch kurz Kontext, damit ich die nächsten Rückfragen passend stellen kann.";

const FOLLOW_UP_DONE_TEXT =
  "Danke, ich nehme die Einordnung mit und gehe an den Plan.";

const FOLLOW_UP_SKIPPED_TEXT =
  "Alles klar, ich mache ohne diese Einordnung weiter.";

const FOLLOW_UP_CONTINUATION_TEXT =
  "Alles klar. Ich nehme das mit auf und verfeinere den Deck-Plan weiter.";

export type FollowUpState =
  | { status: "inactive" }
  | { status: "active"; stepIndex: number; answers: Record<string, string> };

export type ChatState = {
  messages: ChatMessage[];
  followUp: FollowUpState;
};

export type ChatAction =
  | { type: "send-message"; text: string }
  | { type: "answer-follow-up"; answer: string }
  | { type: "go-to-prev-step" }
  | { type: "go-to-next-step" }
  | { type: "skip-follow-up" }
  | { type: "dismiss-follow-up" };

const INACTIVE_FOLLOW_UP: FollowUpState = { status: "inactive" };

const createUserMessage = (text: string): ChatMessage => ({
  id: `user-${crypto.randomUUID()}`,
  role: "user",
  text,
});

const createAssistantMessage = (text: string): ChatMessage => ({
  id: `assistant-${crypto.randomUUID()}`,
  role: "assistant",
  text,
});

export const createInitialChatState = (
  initialPrompt: string | undefined,
): ChatState => {
  if (!initialPrompt) {
    return { messages: [], followUp: INACTIVE_FOLLOW_UP };
  }

  return {
    messages: [
      createUserMessage(initialPrompt),
      createAssistantMessage(FIRST_FOLLOW_UP_TEXT),
    ],
    followUp: { status: "active", stepIndex: 0, answers: {} },
  };
};

export const chatReducer = (
  state: ChatState,
  action: ChatAction,
): ChatState => {
  switch (action.type) {
    case "send-message": {
      const isFirstMessage = state.messages.length === 0;
      const assistantText = isFirstMessage
        ? FIRST_FOLLOW_UP_TEXT
        : FOLLOW_UP_CONTINUATION_TEXT;

      return {
        messages: [
          ...state.messages,
          createUserMessage(action.text),
          createAssistantMessage(assistantText),
        ],
        followUp: isFirstMessage
          ? { status: "active", stepIndex: 0, answers: {} }
          : state.followUp,
      };
    }

    case "answer-follow-up": {
      if (state.followUp.status !== "active") return state;

      const currentStep = followUpSteps[state.followUp.stepIndex];
      if (!currentStep) return state;

      const nextAnswers = {
        ...state.followUp.answers,
        [currentStep.id]: action.answer,
      };
      const isLastStep =
        state.followUp.stepIndex >= followUpSteps.length - 1;

      if (!isLastStep) {
        return {
          ...state,
          followUp: {
            status: "active",
            stepIndex: state.followUp.stepIndex + 1,
            answers: nextAnswers,
          },
        };
      }

      const summary = followUpSteps
        .map((step) => nextAnswers[step.id])
        .filter(Boolean)
        .join(" · ");

      return {
        messages: [
          ...state.messages,
          createUserMessage(summary || "(keine Auswahl)"),
          createAssistantMessage(FOLLOW_UP_DONE_TEXT),
        ],
        followUp: INACTIVE_FOLLOW_UP,
      };
    }

    case "go-to-prev-step": {
      if (state.followUp.status !== "active") return state;
      return {
        ...state,
        followUp: {
          ...state.followUp,
          stepIndex: Math.max(0, state.followUp.stepIndex - 1),
        },
      };
    }

    case "go-to-next-step": {
      if (state.followUp.status !== "active") return state;
      return {
        ...state,
        followUp: {
          ...state.followUp,
          stepIndex: Math.min(
            followUpSteps.length - 1,
            state.followUp.stepIndex + 1,
          ),
        },
      };
    }

    case "skip-follow-up": {
      return {
        messages: [
          ...state.messages,
          createAssistantMessage(FOLLOW_UP_SKIPPED_TEXT),
        ],
        followUp: INACTIVE_FOLLOW_UP,
      };
    }

    case "dismiss-follow-up": {
      return { ...state, followUp: INACTIVE_FOLLOW_UP };
    }
  }
};
