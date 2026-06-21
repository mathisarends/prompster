import type {
  SpotifyExportServerEventSchema,
  SpotifyExportRetryEvent,
  SpotifyPlaylistExportResponse,
} from "@/api/generated/model";
import { AXIOS_INSTANCE } from "@/shared/api/http-client";

export type SpotifyExportServerEvent = NonNullable<SpotifyExportServerEventSchema>;

type StreamSpotifyExportOptions = {
  signal?: AbortSignal;
  onRetry?: (retry: SpotifyExportRetryEvent) => void;
};

const getApiUrl = (path: string) => {
  const baseUrl = String(
    AXIOS_INSTANCE.defaults.baseURL ?? window.location.origin,
  );
  const url = new URL(path, baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`);
  return url.toString();
};

/**
 * Exports the session playlist to Spotify over a server-sent stream. Retries
 * the backend performs against Spotify are surfaced via ``onRetry`` while the
 * export runs; the promise resolves with the created playlist or rejects with
 * the streamed error.
 */
export const streamSpotifyExport = async (
  sessionId: string,
  { signal, onRetry }: StreamSpotifyExportOptions = {},
): Promise<SpotifyPlaylistExportResponse> => {
  const response = await fetch(
    getApiUrl(`/api/v1/sessions/${sessionId}/playlist/spotify`),
    {
      method: "POST",
      credentials: "include",
      signal,
    },
  );

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with status ${response.status}`);
  }

  if (!response.body) {
    throw new Error("Spotify export stream returned no body.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result: SpotifyPlaylistExportResponse | null = null;
  let streamError: Error | null = null;

  const handleEvent = (event: SpotifyExportServerEvent) => {
    switch (event.type) {
      case "spotify_export.retry":
        onRetry?.(event);
        break;
      case "spotify_export.completed":
        result = event.playlist;
        break;
      case "error":
        streamError = new Error(event.message || event.code);
        break;
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

  if (streamError) throw streamError;
  if (!result) {
    throw new Error("Spotify export stream ended without a result.");
  }
  return result;
};

const parseServerSentEvent = (
  rawEvent: string,
): SpotifyExportServerEvent | null => {
  const data = rawEvent
    .split("\n")
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.replace(/^data: ?/, ""))
    .join("\n");

  if (!data) return null;
  return JSON.parse(data) as SpotifyExportServerEvent;
};
