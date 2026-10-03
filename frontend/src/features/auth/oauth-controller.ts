import type { ReactiveController, ReactiveControllerHost } from "lit";
import { resolveApiBaseUrl } from "@api/request";

export type OAuthProvider = "google" | "spotify" | "spotify-connect";
const flows = {
  google: { path: "/api/v1/auth/google/login", type: "prompster-google-oauth" },
  spotify: { path: "/api/v1/auth/spotify/login", type: "prompster-spotify-login" },
  "spotify-connect": { path: "/api/v1/auth/spotify/connect", type: "prompster-spotify-oauth" },
} as const;

function oauthOrigin(): string {
  // In development the provider redirects back to the backend callback origin.
  const explicit = import.meta.env.VITE_OAUTH_BASE_URL || import.meta.env.VITE_API_BASE_URL;
  return explicit
    ? new URL(explicit, window.location.origin).origin
    : import.meta.env.DEV
      ? `${window.location.protocol}//${window.location.hostname}:8000`
      : new URL(resolveApiBaseUrl()).origin;
}

/** Owns popup listeners and timers; the caller verifies the resulting server session. */
export class OAuthController implements ReactiveController {
  pending: OAuthProvider | null = null;
  error = "";
  private popup: Window | null = null;
  private timer?: number;
  private startedAt = 0;
  constructor(
    private host: ReactiveControllerHost,
    private complete: () => Promise<void>,
  ) {
    host.addController(this);
  }
  hostDisconnected(): void {
    this.dispose();
  }
  start(provider: OAuthProvider): void {
    if (this.pending) {
      return;
    }
    this.error = "";
    const flow = flows[provider];
    this.popup = window.open(
      new URL(flow.path, oauthOrigin()),
      flow.type,
      "popup,width=520,height=720",
    );
    if (!this.popup) {
      this.error = "Bitte erlaube Pop-ups, um dich anzumelden.";
      this.host.requestUpdate();
      return;
    }
    this.pending = provider;
    this.startedAt = Date.now();
    window.addEventListener("message", this.onMessage);
    this.timer = window.setInterval(() => {
      if (this.popup?.closed || Date.now() - this.startedAt > 180_000) {
        this.error = "Die Anmeldung wurde geschlossen oder ist abgelaufen. Bitte erneut versuchen.";
        this.dispose();
        this.host.requestUpdate();
      }
    }, 500);
    this.host.requestUpdate();
  }
  private onMessage = async (event: MessageEvent): Promise<void> => {
    if (
      !this.pending ||
      event.origin !== oauthOrigin() ||
      event.source !== this.popup ||
      event.data?.type !== flows[this.pending].type ||
      !["success", "error"].includes(event.data?.status)
    ) {
      return;
    }
    const success = event.data.status === "success";
    this.dispose();
    if (success) {
      try {
        await this.complete();
      } catch {
        this.error = "Die Sitzung konnte nach der Anmeldung nicht geladen werden.";
      }
    } else {
      this.error = "Die Anmeldung wurde abgebrochen oder ist fehlgeschlagen.";
    }
    this.host.requestUpdate();
  };
  private dispose(): void {
    window.removeEventListener("message", this.onMessage);
    window.clearInterval(this.timer);
    this.popup?.close();
    this.popup = null;
    this.pending = null;
  }
}
