import { msg, str } from "@lit/localize";
import type { ReactiveController, ReactiveControllerHost } from "lit";
import { spotifyGetAccessToken } from "@api/generated/spotify";
import { loadSpotifySdk } from "./services/spotify-sdk";
import { errorMessage } from "@shared/events";

export class PlaybackController implements ReactiveController {
  uri: string | null = null;
  paused = true;
  position = 0;
  duration = 0;
  volume = 0.72;
  error = "";
  busy = false;
  private player?: Spotify.Player;
  private deviceId?: string;
  private connecting?: Promise<void>;
  private disposed = false;
  private clock?: number;
  constructor(private host: ReactiveControllerHost) {
    host.addController(this);
  }
  hostConnected(): void {
    this.disposed = false;
  }
  hostDisconnected(): void {
    this.disposed = true;
    this.player?.disconnect();
    this.player = undefined;
    window.clearInterval(this.clock);
  }
  private async connect(): Promise<void> {
    if (this.deviceId && this.player) {
      return;
    }
    if (this.connecting) {
      return this.connecting;
    }
    this.connecting = (async () => {
      const sdk = await loadSpotifySdk();
      if (this.disposed) {
        throw new Error(msg("Player geschlossen"));
      }
      const player = new sdk.Player({
        name: "Prompster Web Player",
        volume: this.volume,
        getOAuthToken: (callback) => {
          void spotifyGetAccessToken()
            .then((result) => callback(result.accessToken))
            .catch((error) => {
              this.error = errorMessage(error);
              this.host.requestUpdate();
            });
        },
      });
      this.player = player;
      player.addListener("player_state_changed", (state) => {
        if (!state) {
          return;
        }
        this.uri = state.track_window.current_track.uri;
        this.paused = state.paused;
        this.position = state.position;
        this.duration = state.duration;
        this.host.requestUpdate();
      });
      player.addListener("not_ready", () => {
        this.deviceId = undefined;
        this.host.requestUpdate();
      });
      await new Promise<void>((resolve, reject) => {
        const timer = window.setTimeout(
          () => reject(new Error(msg("Spotify ist noch nicht bereit. Bitte erneut versuchen."))),
          15_000,
        );
        player.addListener("ready", ({ device_id }) => {
          window.clearTimeout(timer);
          this.deviceId = device_id;
          resolve();
        });
        for (const event of [
          "initialization_error",
          "authentication_error",
          "account_error",
          "playback_error",
        ] as const) {
          player.addListener(event, ({ message }) => {
            window.clearTimeout(timer);
            this.error = message;
            this.host.requestUpdate();
            reject(new Error(message));
          });
        }
        void player
          .connect()
          .then((connected) => {
            if (!connected) {
              window.clearTimeout(timer);
              reject(new Error(msg("Spotify konnte nicht verbunden werden.")));
            }
          })
          .catch(reject);
      });
      this.clock = window.setInterval(() => {
        if (!this.paused) {
          this.position = Math.min(this.position + 1000, this.duration);
          this.host.requestUpdate();
        }
      }, 1000);
    })()
      .catch((error) => {
        this.player?.disconnect();
        this.player = undefined;
        this.deviceId = undefined;
        throw error;
      })
      .finally(() => {
        this.connecting = undefined;
      });
    return this.connecting;
  }
  async toggle(uri: string): Promise<void> {
    if (this.busy) {
      return;
    }
    this.busy = true;
    this.error = "";
    this.host.requestUpdate();
    try {
      await this.connect();
      if (this.disposed) {
        return;
      }
      if (this.uri === uri) {
        await this.player!.togglePlay();
        return;
      }
      await this.player!.activateElement();
      const { accessToken } = await spotifyGetAccessToken();
      const response = await fetch(
        `https://api.spotify.com/v1/me/player/play?device_id=${encodeURIComponent(this.deviceId!)}`,
        {
          method: "PUT",
          headers: { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json" },
          body: JSON.stringify({ uris: [uri] }),
        },
      );
      if (!response.ok) {
        throw new Error(
          response.status === 403
            ? msg("Für die Wiedergabe im Browser ist Spotify Premium erforderlich.")
            : msg(str`Spotify-Wiedergabe fehlgeschlagen (${response.status}).`),
        );
      }
      this.uri = uri;
    } catch (error) {
      this.error = errorMessage(error);
    } finally {
      this.busy = false;
      this.host.requestUpdate();
    }
  }
  async seek(position: number): Promise<void> {
    try {
      await this.player?.seek(position);
      this.position = position;
    } catch (error) {
      this.error = errorMessage(error);
    }
    this.host.requestUpdate();
  }
  async setVolume(volume: number): Promise<void> {
    try {
      await this.player?.setVolume(volume);
      this.volume = volume;
    } catch (error) {
      this.error = errorMessage(error);
    }
    this.host.requestUpdate();
  }
}
