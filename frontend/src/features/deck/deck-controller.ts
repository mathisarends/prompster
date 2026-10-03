import type { ReactiveController, ReactiveControllerHost } from "lit";
import {
  addPlaylistTrack,
  removePlaylistTrack,
  restoreUserCurationEvent,
  exportSessionPlaylist,
} from "@api/generated/sessions";
import type { SpotifyTrackResponse } from "@api/generated/spotify";
import { streamSpotifyExport } from "./api/spotify-export-stream";
import type { SpotifyPlaylistExportResponse } from "@api/session-rpc";
import { emit, errorMessage } from "@shared/events";

export class DeckController implements ReactiveController {
  pending = "";
  error = "";
  retry = "";
  pdfUrl = "";
  exported?: SpotifyPlaylistExportResponse;
  private abort = new AbortController();
  private revision = 0;
  constructor(private host: ReactiveControllerHost & HTMLElement) {
    host.addController(this);
  }
  hostDisconnected(): void {
    this.reset();
  }
  reset(): void {
    this.revision++;
    this.abort.abort();
    this.abort = new AbortController();
    if (this.pdfUrl) {
      URL.revokeObjectURL(this.pdfUrl);
    }
    this.pdfUrl = "";
    this.exported = undefined;
    this.pending = "";
    this.error = "";
  }
  private async run(name: string, action: (signal: AbortSignal) => Promise<void>): Promise<void> {
    if (this.pending) {
      return;
    }
    const revision = this.revision;
    this.pending = name;
    this.error = "";
    this.host.requestUpdate();
    try {
      await action(this.abort.signal);
    } catch (error) {
      if (revision === this.revision) {
        this.error = errorMessage(error);
      }
    } finally {
      if (revision === this.revision) {
        this.pending = "";
        this.host.requestUpdate();
      }
    }
  }
  add(sessionId: string, track: SpotifyTrackResponse): Promise<void> {
    return this.run("add", async (signal) => {
      await addPlaylistTrack(
        sessionId,
        {
          title: track.title,
          artist: track.artist,
          year: track.year,
          spotifyUri: `spotify:track:${track.id}`,
          coverUrl: track.coverUrl,
        },
        { signal },
      );
      signal.throwIfAborted();
      emit(this.host, "deck-changed");
    });
  }
  remove(sessionId: string, trackId: string): Promise<void> {
    return this.run(trackId, async (signal) => {
      await removePlaylistTrack(sessionId, trackId, { signal });
      signal.throwIfAborted();
      emit(this.host, "deck-changed");
    });
  }
  restore(sessionId: string, eventId: string): Promise<void> {
    return this.run(eventId, async (signal) => {
      await restoreUserCurationEvent(sessionId, eventId, { signal });
      signal.throwIfAborted();
      emit(this.host, "deck-changed");
    });
  }
  pdf(sessionId: string, preview: boolean): Promise<void> {
    return this.run("pdf", async (signal) => {
      const blob = await exportSessionPlaylist(sessionId, preview ? { pages: 1 } : undefined, {
        signal,
      });
      signal.throwIfAborted();
      const url = URL.createObjectURL(blob);
      if (preview) {
        if (this.pdfUrl) {
          URL.revokeObjectURL(this.pdfUrl);
        }
        this.pdfUrl = url;
        return;
      }
      const link = document.createElement("a");
      link.href = url;
      link.download = `prompster-${sessionId}.pdf`;
      document.body.append(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
  }
  spotify(sessionId: string): Promise<void> {
    return this.run("spotify", async (signal) => {
      this.retry = "";
      const playlist = await streamSpotifyExport(sessionId, {
        signal,
        onRetry: (event) => {
          this.retry = `Versuch ${event.attempt}/${event.maxAttempts}`;
          this.host.requestUpdate();
        },
      });
      signal.throwIfAborted();
      this.exported = playlist;
    });
  }
}
