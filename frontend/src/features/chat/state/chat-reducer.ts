import type {
  AssistantMessageEntryResponse,
  OnboardingQuestionResponse,
  PlaylistResponse,
  SessionResponse,
  ToolCallSequenceEntryResponse,
  ToolCallResponse,
  UserCurationEventResponse,
  UserMessageEntryResponse,
} from "@/api/generated/model";
import {
  EntryKind,
  ToolCallState,
} from "@/api/generated/model";
import { ServerEventType } from "@/api/session-rpc/models";
import type { PlaylistPayload, SessionSnapshotPayload } from "@/api/session-rpc";
import type { SessionServerEvent } from "@/features/chat/api/session-stream";
import type { ChatAttachment } from "@/features/chat/components/attachments";
import type {
  ToolCallItem,
  ToolCallRetry,
  ToolCallStatus,
} from "@/features/chat/types";

type SessionLike =
  | Pick<
      SessionResponse,
      "id" | "title" | "entries" | "playlist" | "onboardingQuestions" | "phase"
    >
  | SessionSnapshotPayload;
type SessionEntryResponse = SessionResponse["entries"][number];
type PlaylistLike = PlaylistPayload | PlaylistResponse | null | undefined;

export type ChatPlaylist = {
  id: string;
  name?: string | null;
  tracks: PlaylistPayload["tracks"];
  uiRevision: number;
  uiEvent?: "set" | "track_added" | "track_removed" | "track_replaced";
};

export type ChatUserEntry = Omit<UserMessageEntryResponse, "kind"> & {
  kind: typeof EntryKind.user_message;
  isOptimistic?: boolean;
};

export type ChatAssistantEntry = Omit<AssistantMessageEntryResponse, "kind"> & {
  kind: typeof EntryKind.assistant_message;
  isStreaming?: boolean;
};

export type ChatToolCall = ToolCallResponse & {
  // Client-only transient state: the in-flight retry of a still-pending call.
  retry?: ToolCallRetry | null;
};

export type ChatToolCallGroupEntry = Omit<
  ToolCallSequenceEntryResponse,
  "kind" | "calls"
> & {
  kind: "tool_call_group";
  calls: ChatToolCall[];
};

export type ChatEntry =
  | ChatUserEntry
  | ChatAssistantEntry
  | ChatToolCallGroupEntry;

export type ChatState = {
  title?: string;
  entries: ChatEntry[];
  playlist: ChatPlaylist | null;
  isStreaming: boolean;
  pendingInput: PendingInput | null;
  errorMessage?: string;
};

export type PendingInput = {
  kind: string;
  questions: PendingOnboardingQuestion[];
  question?: string | null;
  hint?: string | null;
  options: string[];
  recommendedOption?: string | null;
  selectionMode?: "single_select" | "multi_select";
  questionId?: string | null;
  isLastQuestion?: boolean;
};

export type PendingOnboardingQuestion = {
  id: string;
  sequenceNumber?: number;
  question: string | null;
  hint?: string | null;
  options: string[];
  recommendedOption?: string | null;
  selectionMode: "single_select" | "multi_select";
  isLastQuestion: boolean;
  answers: string[];
  isAnswered: boolean;
};

export const ChatActionType = {
  SESSION_LOADED: "session/loaded",
  SESSION_RESET: "session/reset",
  STREAM_STARTED: "stream/started",
  STREAM_FINISHED: "stream/finished",
  STREAM_STOPPED: "stream/stopped",
  STREAM_FAILED: "stream/failed",
  PENDING_INPUT_CLEAR: "pending_input/clear",
  STREAM_EVENT: "stream/event",
} as const;

const ChatEventType = {
  SESSION_SNAPSHOT: ServerEventType.SESSION_SNAPSHOT,
  TITLE_GENERATED: ServerEventType.SESSION_TITLE_GENERATED,
  ASSISTANT_STARTED: ServerEventType.MESSAGE_ASSISTANT_STARTED,
  ASSISTANT_CHUNK: ServerEventType.MESSAGE_ASSISTANT_CHUNK,
  ASSISTANT_COMPLETED: ServerEventType.MESSAGE_ASSISTANT_COMPLETED,
  ASSISTANT_CANCELLED: ServerEventType.MESSAGE_ASSISTANT_CANCELLED,
  TOOL_CALL_SEQUENCE_ADDED: ServerEventType.TOOL_CALL_SEQUENCE_ADDED,
  TOOL_CALL_RESOLVED: ServerEventType.TOOL_CALL_RESOLVED,
  TOOL_CALL_FAILED: ServerEventType.TOOL_CALL_FAILED,
  TOOL_CALL_RETRY: ServerEventType.TOOL_CALL_RETRY,
  TOOL_CALL_SEQUENCE_COMPLETED: ServerEventType.TOOL_CALL_SEQUENCE_COMPLETED,
  CONTEXT_COMPACTED: ServerEventType.SESSION_CONTEXT_COMPACTED,
  PLAYLIST_SET: ServerEventType.PLAYLIST_SET,
  PLAYLIST_TRACK_ADDED: ServerEventType.PLAYLIST_TRACK_ADDED,
  PLAYLIST_TRACK_REMOVED: ServerEventType.PLAYLIST_TRACK_REMOVED,
  PLAYLIST_TRACK_REPLACED: ServerEventType.PLAYLIST_TRACK_REPLACED,
  ONBOARDING_QUESTION_ASKED: ServerEventType.SESSION_ONBOARDING_QUESTION_ASKED,
  SUSPENDED_FOR_INPUT: ServerEventType.SESSION_SUSPENDED_FOR_INPUT,
  DONE: ServerEventType.DONE,
  ERROR: ServerEventType.ERROR,
} as const;

export type ChatAction =
  | { type: typeof ChatActionType.SESSION_LOADED; session: SessionLike }
  | { type: typeof ChatActionType.SESSION_RESET }
  | {
      type: typeof ChatActionType.STREAM_STARTED;
      userMessageText?: string;
      attachments?: ChatAttachment[];
      userCurationEvents?: UserCurationEventResponse[];
    }
  | { type: typeof ChatActionType.STREAM_FINISHED }
  | { type: typeof ChatActionType.STREAM_STOPPED }
  | { type: typeof ChatActionType.STREAM_FAILED; message: string }
  | { type: typeof ChatActionType.PENDING_INPUT_CLEAR }
  | { type: typeof ChatActionType.STREAM_EVENT; event: SessionServerEvent };

export const createInitialChatState = (): ChatState => ({
  entries: [],
  playlist: null,
  isStreaming: false,
  pendingInput: null,
});

export const chatReducer = (
  state: ChatState,
  action: ChatAction,
): ChatState => {
  switch (action.type) {
    case ChatActionType.SESSION_LOADED:
      return {
        ...state,
        title: action.session.title,
        entries: normalizeSessionEntries(action.session.entries),
        playlist: normalizePlaylist(action.session.playlist),
        pendingInput: getPendingInput(action.session),
        errorMessage: undefined,
      };

    case ChatActionType.SESSION_RESET:
      return createInitialChatState();

    case ChatActionType.STREAM_STARTED:
      return {
        ...state,
        entries: action.userMessageText
          ? [
              ...state.entries,
              createOptimisticUserEntry(
                action.userMessageText,
                action.attachments,
                action.userCurationEvents,
              ),
            ]
          : state.entries,
        isStreaming: true,
        pendingInput: null,
        errorMessage: undefined,
      };

    case ChatActionType.STREAM_FINISHED:
      return {
        ...state,
        entries: finishStreamingAssistantEntries(state.entries),
        isStreaming: false,
      };

    case ChatActionType.STREAM_STOPPED:
      return {
        ...state,
        entries: removeLastPendingToolCall(state.entries),
      };

    case ChatActionType.STREAM_FAILED:
      return {
        ...state,
        entries: upsertStreamErrorEntry(state.entries, action.message),
        isStreaming: false,
        errorMessage: action.message,
      };

    case ChatActionType.PENDING_INPUT_CLEAR:
      return {
        ...state,
        pendingInput: null,
      };

    case ChatActionType.STREAM_EVENT:
      return reduceServerEvent(state, action.event);
  }
};

export const getLatestUserMessageContent = (
  session: SessionLike | undefined,
) => {
  if (!session) return undefined;

  for (let index = session.entries.length - 1; index >= 0; index -= 1) {
    const entry = session.entries[index];
    if (entry.kind === EntryKind.user_message) return entry.content;
  }

  return undefined;
};

export const toToolCallItems = (
  group: ChatToolCallGroupEntry,
): ToolCallItem[] => group.calls.map(toToolCallItem);

export const getScrollKey = (entry: ChatEntry): string => {
  switch (entry.kind) {
    case EntryKind.user_message:
    case EntryKind.assistant_message:
      return `${entry.id}:${entry.content.length}:${entry.kind === EntryKind.assistant_message && entry.isStreaming ? "streaming" : "done"}`;
    case "tool_call_group":
      return `${entry.id}:${entry.label ?? ""}:${entry.calls
        .map(
          (call) =>
            `${call.id}:${call.state}:${call.result?.length ?? 0}:${call.error?.length ?? 0}:${call.resultItems?.length ?? 0}`,
        )
        .join(",")}`;
  }
};

const normalizeSessionEntries = (
  entries: SessionLike["entries"],
): ChatEntry[] => entries.map((entry) => normalizeSessionEntry(entry));

const normalizeSessionEntry = (entry: SessionEntryResponse): ChatEntry => {
  switch (entry.kind) {
    case EntryKind.user_message:
      return normalizeUserEntry(entry);
    case EntryKind.assistant_message:
      return normalizeAssistantEntry(entry);
    case EntryKind.tool_call_sequence:
      return normalizeToolCallGroupEntry(entry);
  }

  if ("calls" in entry) return normalizeToolCallGroupEntry(entry);
  return normalizeAssistantEntry(entry as AssistantMessageEntryResponse);
};

const normalizeUserEntry = (
  entry: UserMessageEntryResponse,
): ChatUserEntry => ({
  ...entry,
  kind: EntryKind.user_message,
});

const normalizeAssistantEntry = (
  entry: AssistantMessageEntryResponse,
): ChatAssistantEntry => ({
  ...entry,
  kind: EntryKind.assistant_message,
  isStreaming: false,
});

const normalizeToolCallGroupEntry = (
  entry: ToolCallSequenceEntryResponse,
): ChatToolCallGroupEntry => ({
  ...entry,
  kind: "tool_call_group",
});

const normalizePlaylist = (playlist: PlaylistLike): ChatPlaylist | null => {
  if (!playlist) return null;
  return {
    id: playlist.id,
    name: playlist.name,
    tracks: playlist.tracks,
    uiRevision: 0,
  };
};

const getPendingInput = (session: SessionLike): PendingInput | null => {
  if (!("onboardingQuestions" in session)) return null;
  // Once onboarding is complete the questions stay on the session for history,
  // but the panel must not reappear.
  if ("phase" in session && session.phase !== "onboarding") return null;

  const questions = (session.onboardingQuestions ?? []).map(
    toPendingOnboardingQuestion,
  );
  if (questions.length === 0) return null;

  // Resume on the first unanswered question, falling back to the first one so a
  // fully answered (but not yet completed) onboarding still renders.
  const activeQuestion =
    questions.find((question) => !question.isAnswered) ?? questions[0];

  return {
    kind: "onboarding_question",
    questions,
    question: activeQuestion.question,
    hint: activeQuestion.hint,
    options: activeQuestion.options,
    recommendedOption: activeQuestion.recommendedOption,
    selectionMode: activeQuestion.selectionMode ?? "single_select",
    questionId: activeQuestion.id,
    isLastQuestion: activeQuestion.isLastQuestion,
  };
};

const toPendingOnboardingQuestion = (
  question: OnboardingQuestionResponse,
): PendingOnboardingQuestion => ({
  id: question.id,
  sequenceNumber: question.sequenceNumber,
  question: question.questionText,
  hint: question.hint ?? null,
  options: question.options ?? [],
  recommendedOption: question.recommendedOption ?? null,
  selectionMode: question.selectionMode ?? "single_select",
  isLastQuestion: question.isLastQuestion,
  answers: question.answers ?? [],
  isAnswered: question.isAnswered ?? false,
});

const nextPlaylistRevision = (playlist: ChatPlaylist | null) =>
  (playlist?.uiRevision ?? 0) + 1;

const addPlaylistTrack = (
  playlist: ChatPlaylist | null,
  playlistId: string,
  track: PlaylistPayload["tracks"][number],
): ChatPlaylist => {
  if (!playlist || playlist.id !== playlistId) {
    return {
      id: playlistId,
      tracks: [track],
      uiRevision: nextPlaylistRevision(playlist),
      uiEvent: "track_added",
    };
  }

  return {
    ...playlist,
    uiRevision: nextPlaylistRevision(playlist),
    uiEvent: "track_added",
    tracks: playlist.tracks.some((candidate) => candidate.id === track.id)
      ? playlist.tracks.map((candidate) =>
          candidate.id === track.id ? track : candidate,
        )
      : [...playlist.tracks, track],
  };
};

const removePlaylistTrack = (
  playlist: ChatPlaylist | null,
  playlistId: string,
  trackId: string,
): ChatPlaylist | null => {
  if (!playlist || playlist.id !== playlistId) return playlist;
  return {
    ...playlist,
    uiRevision: nextPlaylistRevision(playlist),
    uiEvent: "track_removed",
    tracks: playlist.tracks.filter((track) => track.id !== trackId),
  };
};

const replacePlaylistTrack = (
  playlist: ChatPlaylist | null,
  playlistId: string,
  trackId: string,
  track: PlaylistPayload["tracks"][number],
): ChatPlaylist => {
  if (!playlist || playlist.id !== playlistId) {
    return {
      id: playlistId,
      tracks: [track],
      uiRevision: nextPlaylistRevision(playlist),
      uiEvent: "track_replaced",
    };
  }

  const replaced = playlist.tracks.some(
    (candidate) => candidate.id === trackId,
  );
  return {
    ...playlist,
    uiRevision: nextPlaylistRevision(playlist),
    uiEvent: "track_replaced",
    tracks: replaced
      ? playlist.tracks.map((candidate) =>
          candidate.id === trackId ? track : candidate,
        )
      : [...playlist.tracks, track],
  };
};

const reduceServerEvent = (
  state: ChatState,
  event: SessionServerEvent,
): ChatState => {
  if (!event) return state;

  if (
    event.type === ChatEventType.SUSPENDED_FOR_INPUT ||
    event.type === ChatEventType.ONBOARDING_QUESTION_ASKED
  ) {
    const kind =
      event.type === ChatEventType.ONBOARDING_QUESTION_ASKED
        ? "onboarding_question"
        : "kind" in event
          ? event.kind
          : "onboarding_question";

    if (kind !== "onboarding_question") {
      return {
        ...state,
        pendingInput: null,
      };
    }

    const incomingQuestion: PendingOnboardingQuestion = {
      id: event.questionId ?? "",
      question: event.question ?? null,
      hint: event.hint ?? null,
      options: [...(event.options ?? [])],
      recommendedOption: event.recommendedOption ?? null,
      selectionMode: event.selectionMode ?? "single_select",
      isLastQuestion: event.isLastQuestion ?? false,
      answers: [],
      isAnswered: false,
    };
    const currentQuestions =
      state.pendingInput?.kind === "onboarding_question"
        ? state.pendingInput.questions
        : [];
    const existingIndex = currentQuestions.findIndex(
      (question) => question.id && question.id === incomingQuestion.id,
    );
    const questions =
      existingIndex === -1
        ? [...currentQuestions, incomingQuestion]
        : currentQuestions.map((question, index) =>
            index === existingIndex ? incomingQuestion : question,
          );

    return {
      ...state,
      pendingInput: {
        kind,
        questions,
        question: incomingQuestion.question,
        hint: incomingQuestion.hint,
        options: incomingQuestion.options,
        recommendedOption: incomingQuestion.recommendedOption,
        selectionMode: incomingQuestion.selectionMode,
        questionId: incomingQuestion.id || null,
        isLastQuestion: incomingQuestion.isLastQuestion,
      },
    };
  }

  switch (event.type) {
    case ChatEventType.SESSION_SNAPSHOT:
      return {
        ...state,
        title: event.session.title,
        entries: normalizeSessionEntries(event.session.entries),
        playlist: normalizePlaylist(event.session.playlist),
        pendingInput: getPendingInput(event.session),
        errorMessage: undefined,
      };

    case ChatEventType.TITLE_GENERATED:
      return {
        ...state,
        title: event.title,
      };

    case ChatEventType.ASSISTANT_STARTED:
      return {
        ...state,
        entries: startAssistantMessage(
          state.entries,
          event.messageId,
          event.createdAt,
        ),
      };

    case ChatEventType.ASSISTANT_CHUNK:
      return {
        ...state,
        entries: appendAssistantMessageChunk(
          state.entries,
          event.messageId,
          event.chunk,
        ),
      };

    case ChatEventType.ASSISTANT_COMPLETED:
      return {
        ...state,
        entries: upsertChatEntry(
          state.entries,
          normalizeAssistantEntry(event.message),
        ),
      };

    case ChatEventType.ASSISTANT_CANCELLED:
      return {
        ...state,
        entries: cancelAssistantMessage(state.entries, event.messageId),
      };

    case ChatEventType.TOOL_CALL_SEQUENCE_ADDED:
      return {
        ...state,
        entries: upsertChatEntry(
          state.entries,
          normalizeToolCallGroupEntry(event.sequence),
        ),
      };

    case ChatEventType.TOOL_CALL_RESOLVED:
      return {
        ...state,
        entries: updateToolCall(
          state.entries,
          event.sequenceId,
          event.toolCallId,
          {
            state: ToolCallState.completed,
            result: event.result,
            resultItems: event.resultItems ?? [],
            error: null,
            retry: null,
          },
        ),
      };

    case ChatEventType.TOOL_CALL_FAILED:
      return {
        ...state,
        entries: updateToolCall(
          state.entries,
          event.sequenceId,
          event.toolCallId,
          {
            state: ToolCallState.failed,
            result: null,
            error: event.error,
            retry: null,
          },
        ),
      };

    case ChatEventType.TOOL_CALL_RETRY: {
      // sequenceId is best-effort on the backend; fall back to the entry that
      // owns the tool call so a missing id still updates the right chip.
      const sequenceId =
        event.sequenceId ??
        findToolCallSequenceId(state.entries, event.toolCallId);
      if (!sequenceId) return state;

      return {
        ...state,
        entries: updateToolCall(state.entries, sequenceId, event.toolCallId, {
          retry: { attempt: event.attempt, maxAttempts: event.maxAttempts },
        }),
      };
    }

    case ChatEventType.TOOL_CALL_SEQUENCE_COMPLETED:
      return {
        ...state,
        entries: completeToolCallGroup(state.entries, event.sequenceId),
      };

    case ChatEventType.PLAYLIST_SET: {
      const playlist = normalizePlaylist(event.playlist);
      if (!playlist) return { ...state, playlist: null };

      return {
        ...state,
        playlist: {
          ...playlist,
          uiRevision: nextPlaylistRevision(state.playlist),
          uiEvent: "set",
        },
      };
    }

    case ChatEventType.PLAYLIST_TRACK_ADDED:
      return {
        ...state,
        playlist: addPlaylistTrack(
          state.playlist,
          event.playlistId,
          event.track,
        ),
      };

    case ChatEventType.PLAYLIST_TRACK_REMOVED:
      return {
        ...state,
        playlist: removePlaylistTrack(
          state.playlist,
          event.playlistId,
          event.trackId,
        ),
      };

    case ChatEventType.PLAYLIST_TRACK_REPLACED:
      return {
        ...state,
        playlist: replacePlaylistTrack(
          state.playlist,
          event.playlistId,
          event.trackId,
          event.track,
        ),
      };

    case ChatEventType.DONE:
      return {
        ...state,
        entries: finishStreamingAssistantEntries(state.entries),
        isStreaming: false,
      };

    case ChatEventType.ERROR:
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

const createOptimisticUserEntry = (
  text: string,
  attachments: ChatAttachment[] = [],
  userCurationEvents: UserCurationEventResponse[] = [],
): ChatUserEntry => ({
  kind: EntryKind.user_message,
  id: `user-${crypto.randomUUID()}`,
  content: text,
  imageAttachments: attachments
    .map(toOptimisticImageAttachment)
    .filter((attachment): attachment is string => attachment !== null),
  userCurationEvents,
  createdAt: new Date().toISOString(),
  isOptimistic: true,
});

const toOptimisticImageAttachment = (
  attachment: ChatAttachment,
): string | null => {
  if (attachment.kind !== "image") return null;
  return attachment.imageUrl ?? null;
};

const createAssistantEntry = (
  id: string,
  content = "",
  createdAt = new Date().toISOString(),
): ChatAssistantEntry => ({
  kind: EntryKind.assistant_message,
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
  if (entry.kind === EntryKind.assistant_message) {
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
  if (entry.kind === EntryKind.assistant_message) {
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
  if (entry?.kind === EntryKind.assistant_message && !entry.content) {
    return entries.filter((candidate) => candidate.id !== messageId);
  }

  return entries.map((candidate) =>
    candidate.id === messageId && candidate.kind === EntryKind.assistant_message
      ? { ...candidate, isStreaming: false }
      : candidate,
  );
};

const finishStreamingAssistantEntries = (entries: ChatEntry[]) =>
  entries.map((entry) =>
    entry.kind === EntryKind.assistant_message
      ? { ...entry, isStreaming: false }
      : entry,
  );

const updateToolCall = (
  entries: ChatEntry[],
  groupId: string,
  toolCallId: string,
  patch: Partial<
    Pick<ToolCallResponse, "state" | "result" | "resultItems" | "error">
  > & { retry?: ToolCallRetry | null },
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

const findToolCallSequenceId = (
  entries: ChatEntry[],
  toolCallId: string,
): string | undefined => {
  for (const entry of entries) {
    if (entry.kind !== "tool_call_group") continue;
    if (entry.calls.some((call) => call.id === toolCallId)) return entry.id;
  }
  return undefined;
};

const completeToolCallGroup = (entries: ChatEntry[], groupId: string) =>
  entries.map((entry) => {
    if (entry.kind !== "tool_call_group" || entry.id !== groupId) return entry;

    return {
      ...entry,
      calls: entry.calls.map((call) =>
        call.state === ToolCallState.pending
          ? { ...call, state: ToolCallState.completed, retry: null }
          : call,
      ),
    };
  });

const removeLastPendingToolCall = (entries: ChatEntry[]): ChatEntry[] => {
  for (let index = entries.length - 1; index >= 0; index -= 1) {
    const entry = entries[index];
    if (entry.kind !== "tool_call_group") continue;

    const pendingIndex = entry.calls.findLastIndex(
      (call) => call.state === ToolCallState.pending,
    );
    if (pendingIndex === -1) continue;

    const calls = entry.calls.filter(
      (_call, callIndex) => callIndex !== pendingIndex,
    );
    if (calls.length === 0) {
      return entries.filter((_candidate, entryIndex) => entryIndex !== index);
    }

    const nextEntries = [...entries];
    nextEntries[index] = { ...entry, calls };
    return nextEntries;
  }

  return entries;
};

const upsertStreamErrorEntry = (
  entries: ChatEntry[],
  message: string,
): ChatEntry[] => {
  for (let index = entries.length - 1; index >= 0; index -= 1) {
    const entry = entries[index];
    if (entry.kind !== EntryKind.assistant_message || !entry.isStreaming)
      continue;

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
      kind: EntryKind.assistant_message,
      id: `assistant-error-${crypto.randomUUID()}`,
      content: message,
      createdAt: new Date().toISOString(),
      isStreaming: false,
    },
  ];
};

const toToolCallItem = (call: ChatToolCall): ToolCallItem => ({
  id: call.id,
  text: formatToolCallName(call),
  status: toToolCallStatus(call),
  actionType: call.function.actionType,
  detail: getToolCallDetail(call),
  retry: call.retry ?? null,
  resultItems: call.resultItems ?? [],
});

const toToolCallStatus = (call: ToolCallResponse): ToolCallStatus => {
  if (call.state === ToolCallState.pending) return "running";
  if (call.state === ToolCallState.failed) return "failed";
  return "completed";
};

const formatToolCallName = (call: ToolCallResponse) =>
  call.function.statusLabel ?? call.function.name.replaceAll("_", " ");

const getToolCallDetail = (call: ToolCallResponse) => {
  if (call.state === ToolCallState.failed) return call.error ?? undefined;
  if (call.state === ToolCallState.completed) return call.result ?? undefined;

  const argumentKeys = Object.keys(call.function.arguments);
  if (argumentKeys.length === 0) return undefined;

  return JSON.stringify(call.function.arguments, null, 2);
};
