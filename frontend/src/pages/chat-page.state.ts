import type { FollowUpQuestionOption } from "@/components/follow-up-question-flow";
import type { ToolCallItem } from "@/components/tool-call-accordion";

export type ChatRole = "assistant" | "user";

export type ChatMessage = {
  id: string;
  role: ChatRole;
  text: string;
  toolCalls?: ToolCallItem[];
};

export type FollowUpStepConfig = {
  id: string;
  question: string;
  options: FollowUpQuestionOption[];
};

export type FollowUpAnswer = {
  question: string;
  answer: string;
  optionId?: string;
};

export type WorkspacePanelState =
  | { status: "closed" }
  | {
      status: "open";
      kind: "deck-preview";
      description: string;
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

const FOLLOW_UP_CONTINUATION_TEXTS = [
  `## Kontext erfasst ✓

Ich habe deine Eingabe verarbeitet. Hier ein kurzer Überblick, was als Nächstes passiert:

- **Analyse** des Themas anhand deiner Antworten
- **Strukturierung** in logische Abschnitte
- **Generierung** eines ersten Deck-Entwurfs

> Der Entwurf erscheint sobald alle Schritte abgeschlossen sind.`,

  `Alles klar, ich arbeite daran weiter.

Hier ein Beispiel, wie ein Python-Snippet in deinem Deck aussehen könnte:

\`\`\`python
def generate_slide(title: str, bullets: list[str]) -> dict:
    return {
        "title": title,
        "content": bullets,
    }
\`\`\`

Inline-Code wie \`generate_slide()\` wird ebenfalls korrekt gerendert.`,

  `Notiert. Ein paar **wichtige Punkte** zum aktuellen Stand:

| Schritt | Status |
|---|---|
| Kontext aufnehmen | ✅ Erledigt |
| Struktur planen | 🔄 Läuft |
| Deck generieren | ⏳ Ausstehend |

Ich melde mich, sobald der erste Entwurf fertig ist.`,

  `Verstanden. Ich verfeinere den Plan entsprechend.

Zur Erinnerung – du hast bisher folgende Präferenzen angegeben:

1. **Format:** Karten-Deck
2. **Fokus:** Technische Tiefe
3. **Stil:** Prägnant, keine Füllsätze

*Diese Einstellungen fließen direkt in die Generierung ein.*`,
];

const FOLLOW_UP_CONTINUATION_TEXT =
  FOLLOW_UP_CONTINUATION_TEXTS[
    Math.floor(Math.random() * FOLLOW_UP_CONTINUATION_TEXTS.length)
  ];

const WORKSPACE_PANEL_OPEN_TEXT =
  "Ich habe rechts eine Arbeitsfläche geöffnet. Dort kann später der Tool-Output erscheinen.";

const WORKSPACE_PANEL_TEST_TRIGGERS = ["/deck", "/split", "/workspace"];

const EXAMPLE_TOOL_CALLS: ToolCallItem[] = [
  {
    id: "workspace-search",
    text: "Durchsuche Artists und Alben.",
    status: "running",
  },
  {
    id: "read-chat-state",
    text: "Lese vorhandene Trefferliste und normalisiere Namen.",
    status: "pending",
  },
  {
    id: "draft-ui",
    text: "Erstelle Ergebnisvorschlag aus den besten Kandidaten.",
    status: "pending",
  },
];

const createExampleToolCalls = (): ToolCallItem[] =>
  EXAMPLE_TOOL_CALLS.map((call) => ({ ...call }));

export type FollowUpState =
  | { status: "inactive" }
  | {
      status: "active";
      stepIndex: number;
      answers: Record<string, FollowUpAnswer>;
      drafts: Record<string, string>;
    };

export type ChatState = {
  messages: ChatMessage[];
  followUp: FollowUpState;
  workspacePanel: WorkspacePanelState;
};

export const ChatActionType = {
  SendMessage: "send-message",
  UpdateFollowUpDraft: "update-follow-up-draft",
  AnswerFollowUp: "answer-follow-up",
  GoToPrevStep: "go-to-prev-step",
  GoToNextStep: "go-to-next-step",
  SkipFollowUp: "skip-follow-up",
  DismissFollowUp: "dismiss-follow-up",
  OpenWorkspacePanel: "open-workspace-panel",
  CloseWorkspacePanel: "close-workspace-panel",
  AdvanceToolCalls: "advance-tool-calls",
} as const;
export type ChatActionType =
  (typeof ChatActionType)[keyof typeof ChatActionType];

export type ChatAction =
  | { type: typeof ChatActionType.SendMessage; text: string }
  | {
      type: typeof ChatActionType.UpdateFollowUpDraft;
      stepId: string;
      value: string;
    }
  | {
      type: typeof ChatActionType.AnswerFollowUp;
      answer: string;
      option?: FollowUpQuestionOption;
    }
  | { type: typeof ChatActionType.GoToPrevStep }
  | { type: typeof ChatActionType.GoToNextStep }
  | { type: typeof ChatActionType.SkipFollowUp }
  | { type: typeof ChatActionType.DismissFollowUp }
  | { type: typeof ChatActionType.OpenWorkspacePanel }
  | { type: typeof ChatActionType.CloseWorkspacePanel }
  | { type: typeof ChatActionType.AdvanceToolCalls; messageId: string };

const INACTIVE_FOLLOW_UP: FollowUpState = { status: "inactive" };
const CLOSED_WORKSPACE_PANEL: WorkspacePanelState = { status: "closed" };

const createUserMessage = (text: string): ChatMessage => ({
  id: `user-${crypto.randomUUID()}`,
  role: "user",
  text,
});

const createAssistantMessage = (
  text: string,
  toolCalls?: ToolCallItem[],
): ChatMessage => ({
  id: `assistant-${crypto.randomUUID()}`,
  role: "assistant",
  text,
  toolCalls,
});

const createActiveFollowUpState = (): FollowUpState => ({
  status: "active",
  stepIndex: 0,
  answers: {},
  drafts: {},
});

const createDeckWorkspacePanelState = (): WorkspacePanelState => ({
  status: "open",
  kind: "deck-preview",
  description:
    "Platzhalter für den späteren Tool-Output. Noch ohne Playlist-Content.",
});

const shouldOpenWorkspacePanel = (text: string) => {
  const normalizedText = text.trim().toLowerCase();

  return WORKSPACE_PANEL_TEST_TRIGGERS.includes(normalizedText);
};

export const getActiveFollowUpStep = (followUp: FollowUpState) => {
  if (followUp.status !== "active") return undefined;

  return followUpSteps[followUp.stepIndex];
};

export const getFollowUpDraftValue = (followUp: FollowUpState) => {
  const currentStep = getActiveFollowUpStep(followUp);
  if (!currentStep || followUp.status !== "active") return "";

  return (
    followUp.drafts[currentStep.id] ??
    followUp.answers[currentStep.id]?.answer ??
    ""
  );
};

export const getFollowUpStepStatus = (followUp: FollowUpState) => {
  if (followUp.status !== "active") {
    return {
      currentStepIndex: 0,
      totalSteps: followUpSteps.length,
      isFirstStep: true,
      isLastStep: true,
    };
  }

  const currentStepIndex = followUp.stepIndex;

  return {
    currentStepIndex,
    totalSteps: followUpSteps.length,
    isFirstStep: currentStepIndex === 0,
    isLastStep: currentStepIndex === followUpSteps.length - 1,
  };
};

const createFollowUpRetrospectiveText = (
  answers: Record<string, FollowUpAnswer>,
) => {
  const retrospective = followUpSteps
    .map((step) => answers[step.id])
    .filter((answer): answer is FollowUpAnswer => Boolean(answer))
    .map(({ question, answer }) => `F: ${question}\nA: ${answer}`)
    .join("\n\n");

  return retrospective || "(keine Auswahl)";
};

export const createInitialChatState = (
  initialUserMessage: string | undefined,
): ChatState => {
  if (!initialUserMessage) {
    return {
      messages: [],
      followUp: INACTIVE_FOLLOW_UP,
      workspacePanel: CLOSED_WORKSPACE_PANEL,
    };
  }

  return {
    messages: [
      createUserMessage(initialUserMessage),
      createAssistantMessage(FIRST_FOLLOW_UP_TEXT, createExampleToolCalls()),
    ],
    followUp: createActiveFollowUpState(),
    workspacePanel: CLOSED_WORKSPACE_PANEL,
  };
};

export const chatReducer = (
  state: ChatState,
  action: ChatAction,
): ChatState => {
  switch (action.type) {
    case ChatActionType.SendMessage: {
      if (shouldOpenWorkspacePanel(action.text)) {
        return {
          messages: [
            ...state.messages,
            createUserMessage(action.text),
            createAssistantMessage(WORKSPACE_PANEL_OPEN_TEXT),
          ],
          followUp: state.followUp,
          workspacePanel: createDeckWorkspacePanelState(),
        };
      }

      const isFirstMessage = state.messages.length === 0;
      const assistantText = isFirstMessage
        ? FIRST_FOLLOW_UP_TEXT
        : FOLLOW_UP_CONTINUATION_TEXT;

      return {
        messages: [
          ...state.messages,
          createUserMessage(action.text),
          createAssistantMessage(
            assistantText,
            isFirstMessage ? createExampleToolCalls() : undefined,
          ),
        ],
        followUp: isFirstMessage ? createActiveFollowUpState() : state.followUp,
        workspacePanel: state.workspacePanel,
      };
    }

    case ChatActionType.UpdateFollowUpDraft: {
      if (state.followUp.status !== "active") return state;

      return {
        ...state,
        followUp: {
          ...state.followUp,
          drafts: {
            ...state.followUp.drafts,
            [action.stepId]: action.value,
          },
        },
      };
    }

    case ChatActionType.AnswerFollowUp: {
      if (state.followUp.status !== "active") return state;

      const currentStep = followUpSteps[state.followUp.stepIndex];
      if (!currentStep) return state;

      const answer = action.answer.trim();
      if (!answer) return state;

      const nextAnswers = {
        ...state.followUp.answers,
        [currentStep.id]: {
          question: currentStep.question,
          answer,
          optionId: action.option?.id,
        },
      };
      const nextDrafts = {
        ...state.followUp.drafts,
        [currentStep.id]: answer,
      };
      const isLastStep = state.followUp.stepIndex >= followUpSteps.length - 1;

      if (!isLastStep) {
        return {
          ...state,
          followUp: {
            status: "active",
            stepIndex: state.followUp.stepIndex + 1,
            answers: nextAnswers,
            drafts: nextDrafts,
          },
        };
      }

      const retrospective = createFollowUpRetrospectiveText(nextAnswers);

      return {
        messages: [
          ...state.messages,
          createUserMessage(retrospective),
          createAssistantMessage(FOLLOW_UP_DONE_TEXT),
        ],
        followUp: INACTIVE_FOLLOW_UP,
        workspacePanel: state.workspacePanel,
      };
    }

    case ChatActionType.GoToPrevStep: {
      if (state.followUp.status !== "active") return state;
      return {
        ...state,
        followUp: {
          ...state.followUp,
          stepIndex: Math.max(0, state.followUp.stepIndex - 1),
        },
      };
    }

    case ChatActionType.GoToNextStep: {
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

    case ChatActionType.SkipFollowUp: {
      return {
        messages: [
          ...state.messages,
          createAssistantMessage(FOLLOW_UP_SKIPPED_TEXT),
        ],
        followUp: INACTIVE_FOLLOW_UP,
        workspacePanel: state.workspacePanel,
      };
    }

    case ChatActionType.DismissFollowUp: {
      return { ...state, followUp: INACTIVE_FOLLOW_UP };
    }

    case ChatActionType.OpenWorkspacePanel: {
      return {
        ...state,
        messages: [
          ...state.messages,
          createAssistantMessage(WORKSPACE_PANEL_OPEN_TEXT),
        ],
        workspacePanel: createDeckWorkspacePanelState(),
      };
    }

    case ChatActionType.CloseWorkspacePanel: {
      return { ...state, workspacePanel: CLOSED_WORKSPACE_PANEL };
    }

    case ChatActionType.AdvanceToolCalls: {
      const nextMessages = state.messages.map((message) => {
        if (message.id !== action.messageId || !message.toolCalls) {
          return message;
        }

        const runningIndex = message.toolCalls.findIndex(
          (call) => call.status === "running",
        );
        if (runningIndex === -1) return message;

        const nextToolCalls = message.toolCalls.map((call, index) => {
          if (index === runningIndex) return { ...call, status: "completed" as const };
          if (
            index === runningIndex + 1 &&
            call.status === "pending"
          ) {
            return { ...call, status: "running" as const };
          }
          return call;
        });

        return { ...message, toolCalls: nextToolCalls };
      });

      return { ...state, messages: nextMessages };
    }
  }
};

export const findMessageWithRunningToolCall = (messages: ChatMessage[]) =>
  messages.find((message) =>
    message.toolCalls?.some((call) => call.status === "running"),
  );
