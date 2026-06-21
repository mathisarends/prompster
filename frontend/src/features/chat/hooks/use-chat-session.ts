import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import type {
  SessionResponse,
  UserCurationEventResponse,
} from "@/api/generated/model";
import {
  addSpotifyPlaylistTrack,
  getSession,
  getGetSessionQueryKey,
  getListSessionsQueryKey,
  removePlaylistTrack,
  submitOnboardingAnswer,
  stopMessage as stopSessionMessage,
  useGetSession,
} from "@/api/generated/session-api";
import {
  type ImageAttachmentReferenceRequest,
  type SessionMessageAttachmentRequest,
  streamCompleteOnboarding,
  streamSendMessage,
} from "@/features/chat/api/session-stream";
import { uploadImageFile } from "@/features/chat/api/image-attachments";
import type { ChatAttachment } from "@/features/chat/components/attachments";

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
  initialAttachments?: ChatAttachment[];
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
  sendMessage: (
    text: string,
    attachments?: ChatAttachment[],
    userCurationEvents?: UserCurationEventResponse[],
  ) => void;
  persistOnboardingAnswer: (answer: OnboardingAnswerPayload) => void;
  submitOnboardingAnswers: (answers: OnboardingAnswerPayload[]) => void;
  stopMessage: () => void;
  addSpotifyPlaylistTrack: (spotifyUri: string) => Promise<void>;
  addingSpotifyTrackUri: string | null;
  removePlaylistTrack: (trackId: string) => Promise<void>;
};

const getStreamErrorMessage = (error: unknown) => {
  if (error instanceof Error && error.message) return error.message;
  return "Die Antwort konnte nicht geladen werden.";
};

const toReferenceAttachment = (
  attachment: ChatAttachment,
): SessionMessageAttachmentRequest | null => {
  if (attachment.kind === "image" || attachment.kind === "spotify-track") {
    return null;
  }

  return {
    kind: attachment.kind,
    externalId: attachment.spotifyId ?? attachment.id,
    title: attachment.title,
    subtitle: attachment.subtitle ?? null,
    imageUrl: attachment.imageUrl ?? null,
    spotifyId: attachment.spotifyId ?? attachment.id,
  };
};

const toUploadedImageAttachment = (
  attachment: ChatAttachment,
): ImageAttachmentReferenceRequest | null => {
  if (attachment.kind !== "image" || !attachment.storageKey) return null;

  return {
    id: attachment.id,
    storageKey: attachment.storageKey,
    contentType: attachment.contentType ?? attachment.file?.type ?? "image/*",
    fileName: attachment.title,
    sizeBytes: attachment.sizeBytes ?? attachment.file?.size ?? 1,
  };
};

export const useChatSession = ({
  sessionId,
  initialSession,
  streamInitialResponse,
  initialPrompt,
  initialAttachments = [],
}: UseChatSessionParams): UseChatSessionResult => {
  const queryClient = useQueryClient();
  const [state, dispatch] = useReducer(
    chatReducer,
    undefined,
    createInitialChatState,
  );
  const [isStopping, setIsStopping] = useState(false);
  const [addingSpotifyTrackUri, setAddingSpotifyTrackUri] = useState<
    string | null
  >(null);
  const [selectedModel, setSelectedModel] = useState<string | undefined>();

  const abortControllerRef = useRef<AbortController | null>(null);
  const stopAbortTimeoutRef = useRef<number | null>(null);
  const isStreamingRef = useRef(false);
  const isStoppingRef = useRef(false);
  const initialStreamStartedRef = useRef(false);
  const hasStreamedSinceLoadRef = useRef(false);
  const startInitialStreamRef = useRef<(() => void) | null>(null);
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

  const refreshSessionQueries = useCallback(async () => {
    if (!sessionId) return undefined;

    const [updatedSession] = await Promise.all([
      getSession(sessionId),
      queryClient.invalidateQueries({ queryKey: getListSessionsQueryKey() }),
    ]);
    queryClient.setQueryData(getGetSessionQueryKey(sessionId), updatedSession);
    return updatedSession;
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

        const updatedSession = await refreshSessionQueries();
        if (updatedSession) {
          hasStreamedSinceLoadRef.current = false;
          dispatch({ type: "session/loaded", session: updatedSession });
        }
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
    [refreshSessionQueries, sessionId],
  );

  const streamAssistantResponse = useCallback(
    (
      text: string,
      attachments: ChatAttachment[] = [],
      userCurationEvents: UserCurationEventResponse[] = [],
    ) => {
      return runEventStream(
        {
          type: "stream/started",
          userMessageText: text,
          attachments,
          userCurationEvents,
        },
        async (streamOptions) => {
          const imageAttachments = await Promise.all(
            attachments
              .filter((attachment) => attachment.kind === "image")
              .map((attachment) => {
                const uploadedImage = toUploadedImageAttachment(attachment);
                if (uploadedImage) return uploadedImage;
                if (!attachment.file) return null;

                return uploadImageFile(attachment.file, streamOptions.signal);
              })
              .filter(
                (
                  attachment,
                ): attachment is
                  | ImageAttachmentReferenceRequest
                  | Promise<ImageAttachmentReferenceRequest> =>
                  attachment !== null,
              ),
          );
          const referenceAttachments = attachments
            .map(toReferenceAttachment)
            .filter(
              (attachment): attachment is SessionMessageAttachmentRequest =>
                attachment !== null,
            );

          return streamSendMessage(
            sessionId,
            {
              content: text || "Analysiere die angehaengten Bilder.",
              attachments: referenceAttachments,
              imageAttachments,
            },
            {
              ...streamOptions,
              modelId: selectedModel,
            },
          );
        },
      );
    },
    [runEventStream, selectedModel, sessionId],
  );

  const onModelChange = useCallback((modelId: string) => {
    setSelectedModel(modelId);
  }, []);

  // Keep the latest sender in a ref so the initial-stream trigger below does not
  // depend on `streamAssistantResponse`/`initialAttachments` identity. Those
  // change when `selectedModel` is set (e.g. the model picker auto-selecting the
  // default once options load), which would otherwise re-run the trigger effect
  // and cancel the pending initial send before it ever fires. This effect is
  // declared before the trigger so the ref is fresh when the trigger reads it.
  const initialMessage = initialPrompt?.trim();
  useEffect(() => {
    startInitialStreamRef.current =
      streamInitialResponse && initialMessage
        ? () => streamAssistantResponse(initialMessage, initialAttachments)
        : null;
  });

  useEffect(() => {
    if (initialStreamStartedRef.current || !session || state.isStreaming) {
      return;
    }
    if (!startInitialStreamRef.current) return;

    initialStreamStartedRef.current = true;
    const timeoutId = window.setTimeout(() => {
      void startInitialStreamRef.current?.();
    }, 0);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [session, sessionId, state.isStreaming]);

  const sendMessage = useCallback(
    (
      text: string,
      attachments: ChatAttachment[] = [],
      userCurationEvents: UserCurationEventResponse[] = [],
    ) => {
      void streamAssistantResponse(text, attachments, userCurationEvents);
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
      const updatedSession = await refreshSessionQueries();
      if (updatedSession) {
        hasStreamedSinceLoadRef.current = false;
        dispatch({ type: "session/loaded", session: updatedSession });
      }
    },
    [refreshSessionQueries, sessionId],
  );

  const addSpotifyPlaylistTrackToSession = useCallback(
    async (spotifyUri: string) => {
      if (!sessionId || addingSpotifyTrackUri) {
        return;
      }

      setAddingSpotifyTrackUri(spotifyUri);
      try {
        await addSpotifyPlaylistTrack(sessionId, { spotifyUri });
        const updatedSession = await refreshSessionQueries();
        if (updatedSession) {
          hasStreamedSinceLoadRef.current = false;
          dispatch({ type: "session/loaded", session: updatedSession });
        }
      } catch {
        dispatch({
          type: "stream/failed",
          message: "Song konnte nicht hinzugefuegt werden.",
        });
      } finally {
        setAddingSpotifyTrackUri(null);
      }
    },
    [addingSpotifyTrackUri, refreshSessionQueries, sessionId],
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
    addSpotifyPlaylistTrack: addSpotifyPlaylistTrackToSession,
    addingSpotifyTrackUri,
    removePlaylistTrack: removePlaylistTrackFromSession,
  };
};
