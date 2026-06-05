import type {
  AssistantMessageEntryResponse,
  OnboardingQuestionResponse,
  PlaylistPayload,
  PlaylistResponse,
  SessionResponse,
  SessionSnapshotPayload,
  ToolCallSequenceEntryResponse,
  ToolCallResponse,
  UserMessageEntryResponse,
} from "@/api/generated/model";
import type { SessionServerEvent } from "@/api/session-stream";
import type {
  ToolCallItem,
  ToolCallStatus,
} from "@/components/chat/tool-call-sequence";

type SessionLike =
  | Pick<
      SessionResponse,
      "id" | "title" | "entries" | "playlist" | "openOnboardingQuestions"
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
  kind: "user_message";
  isOptimistic?: boolean;
};

export type ChatAssistantEntry = Omit<AssistantMessageEntryResponse, "kind"> & {
  kind: "assistant_message";
  isStreaming?: boolean;
};

export type ChatToolCallGroupEntry = Omit<
  ToolCallSequenceEntryResponse,
  "kind"
> & {
  kind: "tool_call_group";
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
  options: string[];
  selectionMode?: "single_select" | "multi_select";
  questionId?: string | null;
  isLastQuestion?: boolean;
};

export type PendingOnboardingQuestion = {
  id: string;
  sequenceNumber?: number;
  question: string | null;
  options: string[];
  selectionMode: "single_select" | "multi_select";
  isLastQuestion: boolean;
};

export type ChatAction =
  | { type: "session/loaded"; session: SessionLike }
  | { type: "session/reset" }
  | {
      type: "stream/started";
      userMessageText?: string;
    }
  | { type: "stream/finished" }
  | { type: "stream/stopped" }
  | { type: "stream/failed"; message: string }
  | { type: "pending_input/clear" }
  | { type: "stream/event"; event: SessionServerEvent };

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
    case "session/loaded":
      return {
        ...state,
        title: action.session.title,
        entries: normalizeSessionEntries(action.session.entries),
        playlist: normalizePlaylist(action.session.playlist),
        pendingInput: getPendingInput(action.session),
        errorMessage: undefined,
      };

    case "session/reset":
      return createInitialChatState();

    case "stream/started":
      return {
        ...state,
        entries: action.userMessageText
          ? [
              ...state.entries,
              createOptimisticUserEntry(action.userMessageText),
            ]
          : state.entries,
        isStreaming: true,
        pendingInput: null,
        errorMessage: undefined,
      };

    case "stream/finished":
      return {
        ...state,
        entries: finishStreamingAssistantEntries(state.entries),
        isStreaming: false,
      };

    case "stream/stopped":
      return {
        ...state,
        entries: removeLastPendingToolCall(state.entries),
      };

    case "stream/failed":
      return {
        ...state,
        entries: upsertStreamErrorEntry(state.entries, action.message),
        isStreaming: false,
        errorMessage: action.message,
      };

    case "pending_input/clear":
      return {
        ...state,
        pendingInput: null,
      };

    case "stream/event":
      return reduceServerEvent(state, action.event);
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

export const toToolCallItems = (
  group: ChatToolCallGroupEntry,
): ToolCallItem[] => group.calls.map(toToolCallItem);

export const getScrollKey = (entry: ChatEntry): string => {
  switch (entry.kind) {
    case "user_message":
    case "assistant_message":
      return `${entry.id}:${entry.content.length}:${entry.kind === "assistant_message" && entry.isStreaming ? "streaming" : "done"}`;
    case "tool_call_group":
      return `${entry.id}:${entry.calls
        .map(
          (call) =>
            `${call.id}:${call.state}:${call.result?.length ?? 0}:${call.error?.length ?? 0}`,
        )
        .join(",")}`;
  }
};

const normalizeSessionEntries = (
  entries: SessionLike["entries"],
): ChatEntry[] => entries.map((entry) => normalizeSessionEntry(entry));

const normalizeSessionEntry = (entry: SessionEntryResponse): ChatEntry => {
  switch (entry.kind) {
    case "user_message":
      return normalizeUserEntry(entry);
    case "assistant_message":
      return normalizeAssistantEntry(entry);
    case "tool_call_sequence":
      return normalizeToolCallGroupEntry(entry);
  }

  if ("calls" in entry) return normalizeToolCallGroupEntry(entry);
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
  if (!("openOnboardingQuestions" in session)) return null;

  const questions = (session.openOnboardingQuestions ?? []).map(
    toPendingOnboardingQuestion,
  );
  const question = questions[0];
  if (!question) return null;

  return {
    kind: "onboarding_question",
    questions,
    question: question.question,
    options: question.options,
    selectionMode: question.selectionMode ?? "single_select",
    questionId: question.id,
    isLastQuestion: question.isLastQuestion,
  };
};

const toPendingOnboardingQuestion = (
  question: OnboardingQuestionResponse,
): PendingOnboardingQuestion => ({
  id: question.id,
  sequenceNumber: question.sequenceNumber,
  question: question.questionText,
  options: question.options ?? [],
  selectionMode: question.selectionMode ?? "single_select",
  isLastQuestion: question.isLastQuestion,
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
  const eventType = (event as { type?: string }).type;
  if (eventType === "session.suspended_for_input") {
    const payload = event as {
      kind?: string;
      question?: string | null;
      options?: unknown;
      selectionMode?: "single_select" | "multi_select";
      questionId?: string | null;
      isLastQuestion?: boolean;
    };
    const kind = payload.kind ?? "onboarding_question";
    if (kind !== "onboarding_question") {
      return {
        ...state,
        pendingInput: null,
      };
    }
    return {
      ...state,
      pendingInput: {
        kind,
        questions: [
          {
            id: payload.questionId ?? "",
            question: payload.question ?? null,
            options: Array.isArray(payload.options)
              ? payload.options.filter(
                  (option): option is string => typeof option === "string",
                )
              : [],
            selectionMode: payload.selectionMode ?? "single_select",
            isLastQuestion: payload.isLastQuestion ?? false,
          },
        ],
        question: payload.question ?? null,
        options: Array.isArray(payload.options)
          ? payload.options.filter(
              (option): option is string => typeof option === "string",
            )
          : [],
        selectionMode: payload.selectionMode ?? "single_select",
        questionId: payload.questionId ?? null,
        isLastQuestion: payload.isLastQuestion ?? false,
      },
    };
  }

  switch (event.type) {
    case "session.snapshot":
      return {
        ...state,
        title: event.session.title,
        entries: normalizeSessionEntries(event.session.entries),
        playlist: normalizePlaylist(event.session.playlist),
        pendingInput: getPendingInput(event.session),
        errorMessage: undefined,
      };

    case "session.title_generated":
      return {
        ...state,
        title: event.title,
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

    case "tool_call.sequence_added":
      return {
        ...state,
        entries: upsertChatEntry(
          state.entries,
          normalizeToolCallGroupEntry(event.sequence),
        ),
      };

    case "tool_call.resolved":
      return {
        ...state,
        entries: updateToolCall(
          state.entries,
          event.sequenceId,
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
          event.sequenceId,
          event.toolCallId,
          {
            state: "failed",
            result: null,
            error: event.error,
          },
        ),
      };

    case "tool_call.sequence_completed":
      return {
        ...state,
        entries: completeToolCallGroup(state.entries, event.sequenceId),
      };

    case "playlist.set": {
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

    case "playlist.track_added":
      return {
        ...state,
        playlist: addPlaylistTrack(
          state.playlist,
          event.playlistId,
          event.track,
        ),
      };

    case "playlist.track_removed":
      return {
        ...state,
        playlist: removePlaylistTrack(
          state.playlist,
          event.playlistId,
          event.trackId,
        ),
      };

    case "playlist.track_replaced":
      return {
        ...state,
        playlist: replacePlaylistTrack(
          state.playlist,
          event.playlistId,
          event.trackId,
          event.track,
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

const removeLastPendingToolCall = (entries: ChatEntry[]): ChatEntry[] => {
  for (let index = entries.length - 1; index >= 0; index -= 1) {
    const entry = entries[index];
    if (entry.kind !== "tool_call_group") continue;

    const pendingIndex = entry.calls.findLastIndex(
      (call) => call.state === "pending",
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

const toToolCallItem = (call: ToolCallResponse): ToolCallItem => ({
  id: call.id,
  text: formatToolCallName(call),
  status: toToolCallStatus(call),
  actionType: call.function.actionType,
  detail: getToolCallDetail(call),
});

const toToolCallStatus = (call: ToolCallResponse): ToolCallStatus => {
  if (call.state === "pending") return "running";
  if (call.state === "failed") return "failed";
  return "completed";
};

const formatToolCallName = (call: ToolCallResponse) =>
  call.function.statusLabel ?? call.function.name.replaceAll("_", " ");

const getToolCallDetail = (call: ToolCallResponse) => {
  if (call.state === "failed") return call.error ?? undefined;
  if (call.state === "completed") return call.result ?? undefined;

  const argumentKeys = Object.keys(call.function.arguments);
  if (argumentKeys.length === 0) return undefined;

  return JSON.stringify(call.function.arguments, null, 2);
};
