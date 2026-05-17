import type { SendMessageRequest } from "@/api/generated/model";
import { AXIOS_INSTANCE } from "@/api/http-client";

type StreamSendMessageOptions = {
  signal?: AbortSignal;
  onChunk: (chunk: string) => void;
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
  { signal, onChunk }: StreamSendMessageOptions,
) => {
  const response = await fetch(
    getApiUrl(`/api/v1/sessions/${sessionId}/messages`),
    {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
      signal,
    },
  );

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with status ${response.status}`);
  }

  if (!response.body) {
    const text = await response.text();
    if (text) onChunk(text);
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value, { stream: true });
    if (chunk) onChunk(chunk);
  }

  const remainingText = decoder.decode();
  if (remainingText) onChunk(remainingText);
};
