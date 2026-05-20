import type {
  AssistantMessageEntryResponse,
  FollowUpQuestionGroupEntryResponse,
  FollowUpQuestionResponse,
  SessionResponse,
  SessionSnapshotPayload,
  ToolCallGroupEntryResponse,
  ToolCallResponse,
  UserMessageEntryResponse,
} from "@/api/generated/model";
import type { SessionServerEvent } from "@/api/session-stream";
import type {
  ToolCallItem,
  ToolCallStatus,
} from "@/components/chat/tool-call-accordion";

type SessionLike =
  | Pick<SessionResponse, "id" | "title" | "entries">
  | SessionSnapshotPayload;
type SessionEntryResponse = SessionResponse["entries"][number];

export type ChatUserEntry = Omit<UserMessageEntryResponse, "kind"> & {
  kind: "user_message";
  isOptimistic?: boolean;
};

export type ChatAssistantEntry = Omit<AssistantMessageEntryResponse, "kind"> & {
  kind: "assistant_message";
  isStreaming?: boolean;
};

export type ChatToolCallGroupEntry = Omit<
  ToolCallGroupEntryResponse,
  "kind"
> & {
  kind: "tool_call_group";
};

export type ChatFollowUpQuestionGroupEntry = Omit<
  FollowUpQuestionGroupEntryResponse,
  "kind"
> & {
  kind: "follow_up_question_group";
};

export type ChatEntry =
  | ChatUserEntry
  | ChatAssistantEntry
  | ChatToolCallGroupEntry
  | ChatFollowUpQuestionGroupEntry;

export type PendingFollowUpQuestion = {
  group: ChatFollowUpQuestionGroupEntry;
  question: FollowUpQuestionResponse;
  questionIndex: number;
  totalQuestions: number;
};

export type ChatState = {
  title?: string;
  entries: ChatEntry[];
  followUpDrafts: Record<string, string>;
  isStreaming: boolean;
  errorMessage?: string;
};

export type ChatAction =
  | { type: "session/loaded"; session: SessionLike }
  | { type: "session/reset" }
  | {
      type: "stream/started";
      userMessageText?: string;
      skipPendingFollowUps?: boolean;
    }
  | { type: "stream/finished" }
  | { type: "stream/failed"; message: string }
  | { type: "stream/event"; event: SessionServerEvent }
  | { type: "follow-up/draft-changed"; questionId: string; value: string }
  | {
      type: "follow-up/answered";
      groupId: string;
      questionId: string;
      answerText: string;
      optionId?: string;
    }
  | { type: "follow-up/skipped"; groupId: string };

export const createInitialChatState = (): ChatState => ({
  entries: [],
  followUpDrafts: {},
  isStreaming: false,
});

export const chatReducer = (
  state: ChatState,
  action: ChatAction,
): ChatState => {
  switch (action.type) {
    case "session/loaded":
      return {
        ...state,
        title: action.session.title,
        entries: normalizeSessionEntries(action.session.entries),
        errorMessage: undefined,
      };

    case "session/reset":
      return createInitialChatState();

    case "stream/started": {
      const entries = action.skipPendingFollowUps
        ? skipPendingFollowUpEntries(state.entries)
        : state.entries;

      return {
        ...state,
        entries: action.userMessageText
          ? [...entries, createOptimisticUserEntry(action.userMessageText)]
          : entries,
        isStreaming: true,
        errorMessage: undefined,
      };
    }

    case "stream/finished":
      return {
        ...state,
        entries: finishStreamingAssistantEntries(state.entries),
        isStreaming: false,
      };

    case "stream/failed":
      return {
        ...state,
        entries: upsertStreamErrorEntry(state.entries, action.message),
        isStreaming: false,
        errorMessage: action.message,
      };

    case "stream/event":
      return reduceServerEvent(state, action.event);

    case "follow-up/draft-changed":
      return {
        ...state,
        followUpDrafts: {
          ...state.followUpDrafts,
          [action.questionId]: action.value,
        },
      };

    case "follow-up/answered":
      return {
        ...state,
        entries: answerFollowUpQuestion(
          state.entries,
          action.groupId,
          action.questionId,
          action.answerText,
          action.optionId,
        ),
        followUpDrafts: omitDraft(state.followUpDrafts, action.questionId),
      };

    case "follow-up/skipped":
      return {
        ...state,
        entries: skipFollowUpGroup(state.entries, action.groupId),
        followUpDrafts: omitGroupDrafts(
          state.followUpDrafts,
          state.entries,
          action.groupId,
        ),
      };
  }
};

export const getLatestUserMessageContent = (
  session: SessionLike | undefined,
) => {
  if (!session) return undefined;

  for (let index = session.entries.length - 1; index >= 0; index -= 1) {
    const entry = session.entries[index];
    if (entry.kind === "user_message") return entry.content;
  }

  return undefined;
};

export const getPendingFollowUpQuestion = (
  entries: ChatEntry[],
): PendingFollowUpQuestion | undefined => {
  for (let entryIndex = entries.length - 1; entryIndex >= 0; entryIndex -= 1) {
    const entry = entries[entryIndex];
    if (entry.kind !== "follow_up_question_group") continue;

    const questionIndex = entry.questions.findIndex(
      (question) => question.state === "pending",
    );
    if (questionIndex === -1) continue;

    return {
      group: entry,
      question: entry.questions[questionIndex],
      questionIndex,
      totalQuestions: entry.questions.length,
    };
  }

  return undefined;
};

export const toToolCallItems = (
  group: ChatToolCallGroupEntry,
): ToolCallItem[] => group.calls.map(toToolCallItem);

const normalizeSessionEntries = (
  entries: SessionLike["entries"],
): ChatEntry[] => entries.map((entry) => normalizeSessionEntry(entry));

const normalizeSessionEntry = (entry: SessionEntryResponse): ChatEntry => {
  switch (entry.kind) {
    case "user_message":
      return normalizeUserEntry(entry);
    case "assistant_message":
      return normalizeAssistantEntry(entry);
    case "tool_call_group":
      return normalizeToolCallGroupEntry(entry);
    case "follow_up_question_group":
      return normalizeFollowUpQuestionGroupEntry(entry);
  }

  if ("calls" in entry) return normalizeToolCallGroupEntry(entry);
  if ("questions" in entry) return normalizeFollowUpQuestionGroupEntry(entry);

  return normalizeAssistantEntry(entry as AssistantMessageEntryResponse);
};

const normalizeUserEntry = (
  entry: UserMessageEntryResponse,
): ChatUserEntry => ({
  ...entry,
  kind: "user_message",
});

const normalizeAssistantEntry = (
  entry: AssistantMessageEntryResponse,
): ChatAssistantEntry => ({
  ...entry,
  kind: "assistant_message",
  isStreaming: false,
});

const normalizeToolCallGroupEntry = (
  entry: ToolCallGroupEntryResponse,
): ChatToolCallGroupEntry => ({
  ...entry,
  kind: "tool_call_group",
});

const normalizeFollowUpQuestionGroupEntry = (
  entry: FollowUpQuestionGroupEntryResponse,
): ChatFollowUpQuestionGroupEntry => ({
  ...entry,
  kind: "follow_up_question_group",
});

const reduceServerEvent = (
  state: ChatState,
  event: SessionServerEvent,
): ChatState => {
  switch (event.type) {
    case "session.snapshot":
      return {
        ...state,
        title: event.session.title,
        entries: normalizeSessionEntries(event.session.entries),
        errorMessage: undefined,
      };

    case "message.assistant_started":
      return {
        ...state,
        entries: startAssistantMessage(
          state.entries,
          event.messageId,
          event.createdAt,
        ),
      };

    case "message.assistant_chunk":
      return {
        ...state,
        entries: appendAssistantMessageChunk(
          state.entries,
          event.messageId,
          event.chunk,
        ),
      };

    case "message.assistant_completed":
      return {
        ...state,
        entries: upsertChatEntry(
          state.entries,
          normalizeAssistantEntry(event.message),
        ),
      };

    case "message.assistant_cancelled":
      return {
        ...state,
        entries: cancelAssistantMessage(state.entries, event.messageId),
      };

    case "tool_call.group_added":
      return {
        ...state,
        entries: upsertChatEntry(
          state.entries,
          normalizeToolCallGroupEntry(event.group),
        ),
      };

    case "tool_call.resolved":
      return {
        ...state,
        entries: updateToolCall(
          state.entries,
          event.groupId,
          event.toolCallId,
          {
            state: "completed",
            result: event.result,
            error: null,
          },
        ),
      };

    case "tool_call.failed":
      return {
        ...state,
        entries: updateToolCall(
          state.entries,
          event.groupId,
          event.toolCallId,
          {
            state: "failed",
            result: null,
            error: event.error,
          },
        ),
      };

    case "tool_call.group_completed":
      return {
        ...state,
        entries: completeToolCallGroup(state.entries, event.groupId),
      };

    case "follow_up.group_added":
      return {
        ...state,
        entries: upsertChatEntry(
          state.entries,
          normalizeFollowUpQuestionGroupEntry(event.group),
        ),
      };

    case "done":
      return {
        ...state,
        entries: finishStreamingAssistantEntries(state.entries),
        isStreaming: false,
      };

    case "error":
      return {
        ...state,
        entries: upsertStreamErrorEntry(state.entries, event.message),
        isStreaming: false,
        errorMessage: event.message,
      };

    default:
      return state;
  }
};

const createOptimisticUserEntry = (text: string): ChatUserEntry => ({
  kind: "user_message",
  id: `user-${crypto.randomUUID()}`,
  content: text,
  createdAt: new Date().toISOString(),
  isOptimistic: true,
});

const createAssistantEntry = (
  id: string,
  content = "",
  createdAt = new Date().toISOString(),
): ChatAssistantEntry => ({
  kind: "assistant_message",
  id,
  content,
  createdAt,
  isStreaming: true,
});

const upsertChatEntry = (
  entries: ChatEntry[],
  entry: ChatEntry,
): ChatEntry[] => {
  const index = entries.findIndex((candidate) => candidate.id === entry.id);
  if (index === -1) return [...entries, entry];

  const nextEntries = [...entries];
  nextEntries[index] = entry;
  return nextEntries;
};

const startAssistantMessage = (
  entries: ChatEntry[],
  messageId: string,
  createdAt: string,
) => {
  const index = entries.findIndex((entry) => entry.id === messageId);
  if (index === -1) {
    return [...entries, createAssistantEntry(messageId, "", createdAt)];
  }

  const nextEntries = [...entries];
  const entry = nextEntries[index];
  if (entry.kind === "assistant_message") {
    nextEntries[index] = { ...entry, createdAt, isStreaming: true };
  }
  return nextEntries;
};

const appendAssistantMessageChunk = (
  entries: ChatEntry[],
  messageId: string,
  chunk: string,
) => {
  const index = entries.findIndex((entry) => entry.id === messageId);
  if (index === -1) {
    return [...entries, createAssistantEntry(messageId, chunk)];
  }

  const nextEntries = [...entries];
  const entry = nextEntries[index];
  if (entry.kind === "assistant_message") {
    nextEntries[index] = {
      ...entry,
      content: `${entry.content}${chunk}`,
      isStreaming: true,
    };
  }
  return nextEntries;
};

const cancelAssistantMessage = (entries: ChatEntry[], messageId: string) => {
  const entry = entries.find((candidate) => candidate.id === messageId);
  if (entry?.kind === "assistant_message" && !entry.content) {
    return entries.filter((candidate) => candidate.id !== messageId);
  }

  return entries.map((candidate) =>
    candidate.id === messageId && candidate.kind === "assistant_message"
      ? { ...candidate, isStreaming: false }
      : candidate,
  );
};

const finishStreamingAssistantEntries = (entries: ChatEntry[]) =>
  entries.map((entry) =>
    entry.kind === "assistant_message"
      ? { ...entry, isStreaming: false }
      : entry,
  );

const updateToolCall = (
  entries: ChatEntry[],
  groupId: string,
  toolCallId: string,
  patch: Pick<ToolCallResponse, "state"> &
    Partial<Pick<ToolCallResponse, "result" | "error">>,
) =>
  entries.map((entry) => {
    if (entry.kind !== "tool_call_group" || entry.id !== groupId) return entry;

    return {
      ...entry,
      calls: entry.calls.map((call) =>
        call.id === toolCallId ? { ...call, ...patch } : call,
      ),
    };
  });

const completeToolCallGroup = (entries: ChatEntry[], groupId: string) =>
  entries.map((entry) => {
    if (entry.kind !== "tool_call_group" || entry.id !== groupId) return entry;

    return {
      ...entry,
      calls: entry.calls.map((call) =>
        call.state === "pending"
          ? { ...call, state: "completed" as const }
          : call,
      ),
    };
  });

const answerFollowUpQuestion = (
  entries: ChatEntry[],
  groupId: string,
  questionId: string,
  answerText: string,
  optionId: string | undefined,
) =>
  entries.map((entry) => {
    if (entry.kind !== "follow_up_question_group" || entry.id !== groupId) {
      return entry;
    }

    return {
      ...entry,
      questions: entry.questions.map((question) =>
        question.id === questionId
          ? {
              ...question,
              state: "answered" as const,
              answerText,
              answeredOptionId: optionId ?? null,
            }
          : question,
      ),
    };
  });

const skipFollowUpGroup = (entries: ChatEntry[], groupId: string) =>
  entries.map((entry) => {
    if (entry.kind !== "follow_up_question_group" || entry.id !== groupId) {
      return entry;
    }

    return {
      ...entry,
      questions: entry.questions.map((question) =>
        question.state === "pending"
          ? { ...question, state: "skipped" as const }
          : question,
      ),
    };
  });

const skipPendingFollowUpEntries = (entries: ChatEntry[]) =>
  entries.map((entry) => {
    if (entry.kind !== "follow_up_question_group") return entry;

    return {
      ...entry,
      questions: entry.questions.map((question) =>
        question.state === "pending"
          ? { ...question, state: "skipped" as const }
          : question,
      ),
    };
  });

const upsertStreamErrorEntry = (
  entries: ChatEntry[],
  message: string,
): ChatEntry[] => {
  for (let index = entries.length - 1; index >= 0; index -= 1) {
    const entry = entries[index];
    if (entry.kind !== "assistant_message" || !entry.isStreaming) continue;

    const nextEntries = [...entries];
    nextEntries[index] = {
      ...entry,
      content: entry.content || message,
      isStreaming: false,
    };
    return nextEntries;
  }

  return [
    ...entries,
    {
      kind: "assistant_message",
      id: `assistant-error-${crypto.randomUUID()}`,
      content: message,
      createdAt: new Date().toISOString(),
      isStreaming: false,
    },
  ];
};

const omitDraft = (drafts: Record<string, string>, questionId: string) => {
  const { [questionId]: _removed, ...remainingDrafts } = drafts;
  return remainingDrafts;
};

const omitGroupDrafts = (
  drafts: Record<string, string>,
  entries: ChatEntry[],
  groupId: string,
) => {
  const group = entries.find(
    (entry): entry is ChatFollowUpQuestionGroupEntry =>
      entry.kind === "follow_up_question_group" && entry.id === groupId,
  );
  if (!group) return drafts;

  return group.questions.reduce(
    (remainingDrafts, question) => omitDraft(remainingDrafts, question.id),
    drafts,
  );
};

const toToolCallItem = (call: ToolCallResponse): ToolCallItem => ({
  id: call.id,
  text: formatToolCallName(call),
  status: toToolCallStatus(call),
  detail: getToolCallDetail(call),
});

const toToolCallStatus = (call: ToolCallResponse): ToolCallStatus => {
  if (call.state === "pending") return "running";
  if (call.state === "failed") return "failed";
  return "completed";
};

const formatToolCallName = (call: ToolCallResponse) =>
  call.function.name.replaceAll("_", " ");

const getToolCallDetail = (call: ToolCallResponse) => {
  if (call.state === "failed") return call.error ?? undefined;
  if (call.state === "completed") return call.result ?? undefined;

  const argumentKeys = Object.keys(call.function.arguments);
  if (argumentKeys.length === 0) return undefined;

  return JSON.stringify(call.function.arguments, null, 2);
};
