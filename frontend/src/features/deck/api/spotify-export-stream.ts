import { msg } from "@lit/localize";
import type { SpotifyExportRetryEvent, SpotifyPlaylistExportResponse } from "@/api/session-streams";
import { sessionStreams } from "@/shared/api/session-streams";

type StreamSpotifyExportOptions = {
  signal?: AbortSignal;
  onRetry?: (retry: SpotifyExportRetryEvent) => void;
};

export const streamSpotifyExport = async (
  sessionId: string,
  { signal, onRetry }: StreamSpotifyExportOptions = {},
): Promise<SpotifyPlaylistExportResponse> => {
  let result: SpotifyPlaylistExportResponse | undefined;
  for await (const event of sessionStreams().exportSpotify({ sessionId }, { signal })) {
    switch (event.type) {
      case "spotify_export.retry":
        onRetry?.(event);
        break;
      case "spotify_export.completed":
        result = event.playlist;
        break;
      case "error":
        throw new Error(event.message || event.code);
    }
  }
  if (!result) {
    throw new Error(msg("Der Spotify-Export wurde ohne Ergebnis beendet."));
  }
  return result;
};
