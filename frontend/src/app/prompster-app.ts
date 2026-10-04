import { msg, localized } from "@lit/localize";
import { css, html, LitElement, nothing } from "lit";
import { customElement, state } from "lit/decorators.js";
import { queryClient } from "@api/query-client";
import { ApiError } from "@api/request";
import { getMeQuery, type UserMeResponse } from "@api/generated/users";
import { logout } from "@api/generated/auth";
import { pageStyles } from "@shared/styles/page";
import "@features/auth/login-page";
import "./app-layout";
import { routes } from "./routes";

@customElement("prompster-app")
@localized()
export class PrompsterApp extends LitElement {
  @state() private user: UserMeResponse | null = null;
  @state() private loading = true;
  @state() private errorText: (() => string) | null = null;
  private get error(): string {
    return this.errorText?.() ?? "";
  }
  @state() private path = window.location.pathname;
  private authRevision = 0;
  protected willUpdate(): void {
    document
      .querySelector('meta[name="description"]')
      ?.setAttribute(
        "content",
        msg(
          "Deine Musik. Deine Erinnerungen. Dein Kartendeck. Gestalte deinen nächsten Spieleabend mit Prompster.",
        ),
      );
  }
  connectedCallback(): void {
    super.connectedCallback();
    window.addEventListener("popstate", this.pop);
    void this.resolveSession();
  }
  disconnectedCallback(): void {
    this.authRevision++;
    window.removeEventListener("popstate", this.pop);
    super.disconnectedCallback();
  }
  private pop = (): void => {
    this.path = window.location.pathname;
  };
  private navigate(path: string, replace = false): void {
    if (path !== this.path) {
      history[replace ? "replaceState" : "pushState"]({}, "", path);
      this.path = path;
    }
  }
  private resolveSession = async (): Promise<void> => {
    const revision = ++this.authRevision;
    this.errorText = null;
    try {
      const user = await queryClient.fetchQuery({ ...getMeQuery(), staleTime: 0, retry: false });
      if (revision !== this.authRevision) {
        return;
      }
      this.user = user;
      if (this.path === routes.landing) {
        this.navigate(routes.new, true);
      }
    } catch (error) {
      if (revision !== this.authRevision) {
        return;
      }
      this.user = null;
      if (!(error instanceof ApiError && error.status === 401)) {
        this.errorText = () => msg("Die Verbindung zum Server ist gerade nicht verfügbar.");
      }
    } finally {
      if (revision === this.authRevision) {
        this.loading = false;
      }
    }
  };
  private signIn = async (): Promise<void> => {
    queryClient.clear();
    await this.resolveSession();
    if (!this.user) {
      throw new Error("Session unavailable");
    }
  };
  private signOut = async (): Promise<void> => {
    try {
      await logout();
      this.authRevision++;
      queryClient.clear();
      this.user = null;
      this.navigate(routes.landing);
    } catch {
      this.errorText = () => msg("Abmelden fehlgeschlagen. Bitte erneut versuchen.");
    }
  };
  static styles = css`
    ${pageStyles} :host {
      display: block;
    }
    .loading {
      min-height: 100dvh;
      display: grid;
      place-items: center;
    }
    .global-error {
      position: fixed;
      bottom: 12px;
      left: 50%;
      transform: translateX(-50%);
      z-index: 100;
    }
  `;
  render() {
    if (this.loading) {
      return html`<div class="loading" role="status">
        ${msg("Dein Deckstudio wird geladen …")}
      </div>`;
    }
    if (!this.user) {
      return html`<login-page
        .onAuthenticated=${this.signIn}
        .connectionError=${this.error}
        @retry-auth=${this.resolveSession}
      ></login-page>`;
    }
    return html`<app-layout
        .path=${this.path}
        .user=${this.user}
        @navigate=${(event: CustomEvent<string>) => this.navigate(event.detail)}
        @sign-out=${this.signOut}
        @user-refresh=${this.resolveSession}
      ></app-layout
      >${this.error ? html`<div class="error global-error" role="alert">${this.error}<button class="text-button" @click=${() => (this.errorText = null)}>${msg("Schließen")}</button></div>` : nothing}`;
  }
}
