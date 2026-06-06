import type {
  SendMessageRequest,
  SessionServerEvent as SessionServerEventPayload,
} from "@/api/generated/model";
import { AXIOS_INSTANCE } from "@/shared/api/http-client";

export type SessionServerEvent = NonNullable<SessionServerEventPayload>;

type StreamSendMessageOptions = {
  signal?: AbortSignal;
  onChunk?: (chunk: string) => void;
  onDone?: () => void;
  onEvent?: (event: SessionServerEvent) => void;
};

const getApiUrl = (path: string) => {
  const baseUrl = String(
    AXIOS_INSTANCE.defaults.baseURL ?? window.location.origin,
  );
  return new URL(
    path,
    baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`,
  ).toString();
};

export const streamSendMessage = async (
  sessionId: string,
  body: SendMessageRequest,
  options: StreamSendMessageOptions,
) =>
  streamSessionRequest(`/api/v1/sessions/${sessionId}/messages`, body, options);

const streamSessionRequest = async (
  path: string,
  body: SendMessageRequest,
  { signal, onChunk, onDone, onEvent }: StreamSendMessageOptions,
) => {
  const response = await fetch(getApiUrl(path), {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
    signal,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with status ${response.status}`);
  }

  const contentType = response.headers.get("content-type") ?? "";

  if (!response.body) {
    const text = await response.text();
    if (text) onChunk?.(text);
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  if (!contentType.includes("text/event-stream")) {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      if (chunk) onChunk?.(chunk);
    }

    const remainingText = decoder.decode();
    if (remainingText) onChunk?.(remainingText);
    return;
  }

  let buffer = "";

  const handleEvent = (event: SessionServerEvent) => {
    onEvent?.(event);

    switch (event.type) {
      case "message.assistant_chunk":
        onChunk?.(event.chunk);
        break;
      case "done":
        onDone?.();
        break;
      case "error":
        throw new Error(event.message || event.code);
    }
  };

  const flushEvents = (flushRemaining = false) => {
    buffer = buffer.replaceAll("\r\n", "\n");

    while (true) {
      const boundaryIndex = buffer.indexOf("\n\n");
      if (boundaryIndex === -1) break;

      const rawEvent = buffer.slice(0, boundaryIndex);
      buffer = buffer.slice(boundaryIndex + 2);
      const event = parseServerSentEvent(rawEvent);
      if (event) handleEvent(event);
    }

    if (flushRemaining && buffer.trim()) {
      const event = parseServerSentEvent(buffer);
      buffer = "";
      if (event) handleEvent(event);
    }
  };

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value, { stream: true });
    if (chunk) {
      buffer += chunk;
      flushEvents();
    }
  }

  buffer += decoder.decode();
  flushEvents(true);
};

const parseServerSentEvent = (rawEvent: string): SessionServerEvent | null => {
  const data = rawEvent
    .split("\n")
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.replace(/^data: ?/, ""))
    .join("\n");

  if (!data) return null;
  return JSON.parse(data) as SessionServerEvent;
};
