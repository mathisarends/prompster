import { msg } from "@lit/localize";
import type { SpotifyExportRetryEvent, SpotifyPlaylistExportResponse } from "@/api/session-rpc";
import { withSessionRpcClient } from "@/shared/api/session-rpc-client";

type StreamSpotifyExportOptions = {
  signal?: AbortSignal;
  onRetry?: (retry: SpotifyExportRetryEvent) => void;
};

export const streamSpotifyExport = (
  sessionId: string,
  { signal, onRetry }: StreamSpotifyExportOptions = {},
): Promise<SpotifyPlaylistExportResponse> =>
  withSessionRpcClient(sessionId, signal, async (client) => {
    let result: SpotifyPlaylistExportResponse | undefined;
    for await (const event of client.session.exportSpotify()) {
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
  });
