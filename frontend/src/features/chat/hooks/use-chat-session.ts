import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import type { SessionResponse } from "@/api/generated/model";
import {
  getGetSessionQueryKey,
  getListSessionsQueryKey,
  removePlaylistTrack,
  submitOnboardingAnswer,
  stopMessage as stopSessionMessage,
  useGetSession,
} from "@/api/generated/session-api";
import {
  streamCompleteOnboarding,
  streamSendMessage,
} from "@/features/chat/api/session-stream";

import {
  chatReducer,
  createInitialChatState,
  type ChatAction,
  type ChatEntry,
  type ChatPlaylist,
  type PendingInput,
} from "../state/chat-reducer";

type StreamOptions = Parameters<typeof streamSendMessage>[2];
type OnboardingAnswerPayload = {
  questionId: string;
  answer: string;
  answers?: string[];
  isLastQuestion?: boolean;
};

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
  isTitlePending: boolean;
  isStreaming: boolean;
  isStopping: boolean;
  pendingInput: PendingInput | null;
  errorMessage?: string;
  isLoadingSession: boolean;
  isError: boolean;
  selectedModel?: string;
  onModelChange: (modelId: string) => void;
  sendMessage: (text: string) => void;
  persistOnboardingAnswer: (answer: OnboardingAnswerPayload) => void;
  submitOnboardingAnswers: (answers: OnboardingAnswerPayload[]) => void;
  stopMessage: () => void;
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
  const [isStopping, setIsStopping] = useState(false);
  const [selectedModel, setSelectedModel] = useState<string | undefined>();

  const abortControllerRef = useRef<AbortController | null>(null);
  const stopAbortTimeoutRef = useRef<number | null>(null);
  const isStreamingRef = useRef(false);
  const isStoppingRef = useRef(false);
  const initialStreamStartedRef = useRef(false);
  const hasStreamedSinceLoadRef = useRef(false);
  const onboardingPersistenceQueueRef = useRef<Promise<void>>(
    Promise.resolve(),
  );

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
      if (stopAbortTimeoutRef.current !== null) {
        window.clearTimeout(stopAbortTimeoutRef.current);
      }
      abortControllerRef.current?.abort();
    },
    [],
  );

  useEffect(() => {
    if (stopAbortTimeoutRef.current !== null) {
      window.clearTimeout(stopAbortTimeoutRef.current);
      stopAbortTimeoutRef.current = null;
    }
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    isStreamingRef.current = false;
    isStoppingRef.current = false;
    initialStreamStartedRef.current = false;
    hasStreamedSinceLoadRef.current = false;
    dispatch({ type: "session/reset" });

    const resetStoppingTimeout = window.setTimeout(() => {
      setIsStopping(false);
    }, 0);
    return () => {
      window.clearTimeout(resetStoppingTimeout);
    };
  }, [sessionId]);

  useEffect(() => {
    isStreamingRef.current = state.isStreaming;
  }, [state.isStreaming]);

  useEffect(() => {
    if (!session || session.id !== sessionId || state.isStreaming) return;
    if (hasStreamedSinceLoadRef.current) return;
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
      hasStreamedSinceLoadRef.current = true;
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
        if (stopAbortTimeoutRef.current !== null) {
          window.clearTimeout(stopAbortTimeoutRef.current);
          stopAbortTimeoutRef.current = null;
        }
        if (abortControllerRef.current === controller) {
          abortControllerRef.current = null;
        }
        isStreamingRef.current = false;
        isStoppingRef.current = false;
        setIsStopping(false);
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
        },
        (streamOptions) =>
          streamSendMessage(
            sessionId,
            { content: text },
            {
              ...streamOptions,
              modelId: selectedModel,
            },
          ),
      );
    },
    [runEventStream, selectedModel, sessionId],
  );

  const onModelChange = useCallback((modelId: string) => {
    setSelectedModel(modelId);
  }, []);

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

  const normalizeOnboardingAnswer = useCallback(
    (answer: OnboardingAnswerPayload) => {
      const answers = (
        answer.answers?.length ? answer.answers : [answer.answer]
      )
        .map((value) => value.trim())
        .filter(Boolean);
      if (!answer.questionId || answers.length === 0) return null;

      return {
        ...answer,
        answer: answers.join(", "),
        answers,
      };
    },
    [],
  );

  const persistOnboardingAnswer = useCallback(
    (answer: OnboardingAnswerPayload) => {
      const normalizedAnswer = normalizeOnboardingAnswer(answer);
      if (!normalizedAnswer || !sessionId) return;

      const request = onboardingPersistenceQueueRef.current.then(async () => {
        await submitOnboardingAnswer(sessionId, {
          questionId: normalizedAnswer.questionId,
          answer: normalizedAnswer.answer,
          answers: normalizedAnswer.answers,
        });
      });
      onboardingPersistenceQueueRef.current = request.catch((error) => {
        dispatch({
          type: "stream/failed",
          message: getStreamErrorMessage(error),
        });
      });
    },
    [normalizeOnboardingAnswer, sessionId],
  );

  const submitOnboardingAnswers = useCallback(
    (answers: OnboardingAnswerPayload[]) => {
      const normalizedAnswers = answers
        .map(normalizeOnboardingAnswer)
        .filter((answer) => answer !== null);
      if (normalizedAnswers.length === 0) return;

      void (async () => {
        await runEventStream(
          { type: "stream/started" },
          async (streamOptions) => {
            await onboardingPersistenceQueueRef.current;
            for (const answer of normalizedAnswers) {
              await submitOnboardingAnswer(sessionId, {
                questionId: answer.questionId,
                answer: answer.answer,
                answers: answer.answers,
              });

              if (answer.isLastQuestion) {
                await streamCompleteOnboarding(sessionId, {
                  ...streamOptions,
                  modelId: selectedModel,
                });
                return;
              }
            }
          },
        );
      })();
    },
    [normalizeOnboardingAnswer, runEventStream, selectedModel, sessionId],
  );

  const stopMessage = useCallback(() => {
    if (!sessionId || !isStreamingRef.current || isStoppingRef.current) return;

    isStoppingRef.current = true;
    setIsStopping(true);

    void (async () => {
      try {
        await stopSessionMessage(sessionId);
        dispatch({ type: "stream/stopped" });
      } catch {
        abortControllerRef.current?.abort();
        return;
      }

      if (!abortControllerRef.current) {
        isStoppingRef.current = false;
        setIsStopping(false);
        return;
      }

      stopAbortTimeoutRef.current = window.setTimeout(() => {
        abortControllerRef.current?.abort();
      }, 1500);
    })();
  }, [sessionId]);

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

  const resolvedTitle = state.title ?? session?.title;
  const isTitlePending = !resolvedTitle?.trim();

  return {
    session,
    title: resolvedTitle,
    entries: state.entries,
    playlist: state.playlist,
    isTitlePending,
    isStreaming: state.isStreaming,
    isStopping,
    pendingInput: state.pendingInput,
    errorMessage: state.errorMessage,
    isLoadingSession: isLoading && state.entries.length === 0,
    isError,
    selectedModel,
    onModelChange,
    sendMessage,
    persistOnboardingAnswer,
    submitOnboardingAnswers,
    stopMessage,
    removePlaylistTrack: removePlaylistTrackFromSession,
  };
};
