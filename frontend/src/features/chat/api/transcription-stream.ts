import { resolveApiBaseUrl } from "@/shared/api/http-client";

export const TranscriptionServerEventType = {
  SessionConnected: "session_connected",
  TranscriptDelta: "transcript_delta",
  TranscriptCompleted: "transcript_completed",
  SpeechStarted: "speech_started",
  SpeechStopped: "speech_stopped",
  TranscriberError: "transcriber_error",
  Error: "error",
} as const;

export type TranscriptionServerEventType =
  (typeof TranscriptionServerEventType)[keyof typeof TranscriptionServerEventType];

export type TranscriptionServerEvent =
  | { type: typeof TranscriptionServerEventType.SessionConnected }
  | {
      type: typeof TranscriptionServerEventType.TranscriptDelta;
      delta: string;
      itemId: string;
    }
  | {
      type: typeof TranscriptionServerEventType.TranscriptCompleted;
      transcript: string;
      itemId: string;
    }
  | {
      type: typeof TranscriptionServerEventType.SpeechStarted;
      itemId: string;
      audioStartMs: number;
    }
  | {
      type: typeof TranscriptionServerEventType.SpeechStopped;
      itemId: string;
      audioEndMs: number;
    }
  | {
      type: typeof TranscriptionServerEventType.TranscriberError;
      error: { type: string; message: string };
    }
  | { type: typeof TranscriptionServerEventType.Error; message: string };

export const resolveTranscriptionWebSocketUrl = (): string => {
  const url = new URL("/api/v1/transcription/realtime", resolveApiBaseUrl());
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
};

export const parseTranscriptionEvent = (
  rawMessage: string,
): TranscriptionServerEvent => {
  return JSON.parse(rawMessage) as TranscriptionServerEvent;
};
