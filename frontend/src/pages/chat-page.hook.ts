import { useCallback, useEffect, useReducer, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";

import type {
  FollowUpQuestionResponse,
  FollowUpRequest,
  SessionResponse,
} from "@/api/generated/model";
import {
  getGetSessionQueryKey,
  getListSessionsQueryKey,
  removePlaylistTrack,
  useGetSession,
} from "@/api/generated/session-api";
import { streamFollowUp, streamSendMessage } from "@/api/session-stream";
import type { FollowUpQuestionOption } from "@/components/chat/follow-up-question-flow";

import {
  chatReducer,
  createInitialChatState,
  type ChatAction,
  type ChatEntry,
  type ChatPlaylist,
} from "./chat-page.state";

type StreamOptions = Parameters<typeof streamSendMessage>[2];

type UseChatSessionParams = {
  sessionId: string;
  initialSession?: SessionResponse;
  streamInitialResponse?: boolean;
  initialPrompt?: string;
};

export type UseChatSessionResult = {
  session?: SessionResponse;
  title?: string;
  entries: ChatEntry[];
  playlist: ChatPlaylist | null;
  followUpDrafts: Record<string, string>;
  isStreaming: boolean;
  errorMessage?: string;
  isLoadingSession: boolean;
  isError: boolean;
  sendMessage: (text: string) => void;
  answerFollowUp: (
    groupId: string,
    question: FollowUpQuestionResponse,
    answer: string,
    option?: FollowUpQuestionOption,
  ) => void;
  skipFollowUps: (groupId: string) => void;
  updateFollowUpDraft: (questionId: string, value: string) => void;
  removePlaylistTrack: (trackId: string) => Promise<void>;
};

const getStreamErrorMessage = (error: unknown) => {
  if (error instanceof Error && error.message) return error.message;
  return "Die Antwort konnte nicht geladen werden.";
};

export const useChatSession = ({
  sessionId,
  initialSession,
  streamInitialResponse,
  initialPrompt,
}: UseChatSessionParams): UseChatSessionResult => {
  const queryClient = useQueryClient();
  const [state, dispatch] = useReducer(
    chatReducer,
    undefined,
    createInitialChatState,
  );

  const abortControllerRef = useRef<AbortController | null>(null);
  const isStreamingRef = useRef(false);
  const initialStreamStartedRef = useRef(false);

  const {
    data: session,
    isError,
    isLoading,
  } = useGetSession(sessionId, {
    query: {
      enabled: Boolean(sessionId),
      initialData: initialSession,
    },
  });

  useEffect(
    () => () => {
      abortControllerRef.current?.abort();
    },
    [],
  );

  useEffect(() => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    isStreamingRef.current = false;
    initialStreamStartedRef.current = false;
    dispatch({ type: "session/reset" });
  }, [sessionId]);

  useEffect(() => {
    isStreamingRef.current = state.isStreaming;
  }, [state.isStreaming]);

  useEffect(() => {
    if (!session || session.id !== sessionId || state.isStreaming) return;
    dispatch({ type: "session/loaded", session });
  }, [session, sessionId, state.isStreaming]);

  const invalidateSessionQueries = useCallback(async () => {
    if (!sessionId) return;
    await Promise.all([
      queryClient.invalidateQueries({
        queryKey: getGetSessionQueryKey(sessionId),
      }),
      queryClient.invalidateQueries({ queryKey: getListSessionsQueryKey() }),
    ]);
  }, [queryClient, sessionId]);

  const runEventStream = useCallback(
    async (
      startAction: ChatAction,
      streamRequest: (options: StreamOptions) => Promise<void>,
    ) => {
      if (!sessionId || isStreamingRef.current) return;

      const controller = new AbortController();
      let streamErrorReceived = false;

      isStreamingRef.current = true;
      abortControllerRef.current = controller;
      dispatch(startAction);

      try {
        await streamRequest({
          signal: controller.signal,
          onEvent: (event) => {
            if (event.type === "error") streamErrorReceived = true;
            dispatch({ type: "stream/event", event });
          },
        });

        await invalidateSessionQueries();
      } catch (error) {
        if (!controller.signal.aborted && !streamErrorReceived) {
          dispatch({
            type: "stream/failed",
            message: getStreamErrorMessage(error),
          });
        }
      } finally {
        if (abortControllerRef.current === controller) {
          abortControllerRef.current = null;
        }
        isStreamingRef.current = false;
        dispatch({ type: "stream/finished" });
      }
    },
    [invalidateSessionQueries, sessionId],
  );

  const streamAssistantResponse = useCallback(
    (text: string) => {
      return runEventStream(
        {
          type: "stream/started",
          userMessageText: text,
          skipPendingFollowUps: true,
        },
        (streamOptions) =>
          streamSendMessage(sessionId, { content: text }, streamOptions),
      );
    },
    [runEventStream, sessionId],
  );

  const streamFollowUpResponse = useCallback(
    (body: FollowUpRequest) =>
      runEventStream({ type: "stream/started" }, (streamOptions) =>
        streamFollowUp(sessionId, body, streamOptions),
      ),
    [runEventStream, sessionId],
  );

  useEffect(() => {
    if (
      !streamInitialResponse ||
      initialStreamStartedRef.current ||
      !session ||
      state.isStreaming
    ) {
      return;
    }

    const initialMessage = initialPrompt?.trim();
    if (!initialMessage) return;

    initialStreamStartedRef.current = true;
    const timeoutId = window.setTimeout(() => {
      void streamAssistantResponse(initialMessage);
    }, 0);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [
    session,
    state.isStreaming,
    streamAssistantResponse,
    streamInitialResponse,
    initialPrompt,
  ]);

  const sendMessage = useCallback(
    (text: string) => {
      void streamAssistantResponse(text);
    },
    [streamAssistantResponse],
  );

  const answerFollowUp = useCallback(
    (
      groupId: string,
      question: FollowUpQuestionResponse,
      answer: string,
      option?: FollowUpQuestionOption,
    ) => {
      if (isStreamingRef.current) return;

      dispatch({
        type: "follow-up/answered",
        groupId,
        questionId: question.id,
        answerText: answer,
        optionId: option?.id,
      });
      void streamFollowUpResponse({
        action: "answer",
        answers: [
          option
            ? { questionId: question.id, optionId: option.id }
            : { questionId: question.id, text: answer },
        ],
      });
    },
    [streamFollowUpResponse],
  );

  const skipFollowUps = useCallback(
    (groupId: string) => {
      if (isStreamingRef.current) return;
      dispatch({ type: "follow-up/skipped", groupId });
      void streamFollowUpResponse({ action: "skip_remaining" });
    },
    [streamFollowUpResponse],
  );

  const updateFollowUpDraft = useCallback(
    (questionId: string, value: string) => {
      dispatch({ type: "follow-up/draft-changed", questionId, value });
    },
    [],
  );

  const removePlaylistTrackFromSession = useCallback(
    async (trackId: string) => {
      if (!sessionId) {
        return;
      }

      await removePlaylistTrack(sessionId, trackId);
      await invalidateSessionQueries();
    },
    [invalidateSessionQueries, sessionId],
  );

  return {
    session,
    title: state.title ?? session?.title,
    entries: state.entries,
    playlist: state.playlist,
    followUpDrafts: state.followUpDrafts,
    isStreaming: state.isStreaming,
    errorMessage: state.errorMessage,
    isLoadingSession: isLoading && state.entries.length === 0,
    isError,
    sendMessage,
    answerFollowUp,
    skipFollowUps,
    updateFollowUpDraft,
    removePlaylistTrack: removePlaylistTrackFromSession,
  };
};
