import { css, html, LitElement, nothing, type PropertyValues } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { UserMeResponse } from "@api/generated/users";
import { pageStyles } from "@shared/styles/page";
import { icon } from "@shared/ui/icons";
import { emit, errorMessage } from "@shared/events";
import { SessionsController } from "@features/sessions/sessions-controller";
import { chatPath, sessionIdFromPath } from "./routes";
import "@shared/ui/sidebar";
import "@shared/ui/breadcrumb";
import "@features/chat/chat-page";
import "@features/sessions/library-page";
import "@features/settings/settings-page";

@customElement("app-layout")
export class AppLayout extends LitElement {
  @property() path = "/new";
  @property({ attribute: false }) user!: UserMeResponse;
  @state() private sidebarOpen = window.innerWidth > 800;
  @state() private selectedId = "";
  @state() private deckTitle = "";
  @state() private error = "";
  private sessions = new SessionsController(this);
  connectedCallback(): void {
    super.connectedCallback();
    window.addEventListener("keydown", this.keydown);
  }
  disconnectedCallback(): void {
    window.removeEventListener("keydown", this.keydown);
    super.disconnectedCallback();
  }
  protected willUpdate(changed: PropertyValues): void {
    if (changed.has("path")) {
      document.title = `${this.path === "/decks" ? "Meine Decks" : this.path === "/settings" ? "Einstellungen" : "Deckstudio"} · Prompster`;
      if (window.innerWidth <= 800) {
        this.sidebarOpen = false;
      }
    }
  }
  private keydown = (event: KeyboardEvent): void => {
    if (event.key === "Escape") {
      if (window.innerWidth <= 800) {
        this.sidebarOpen = false;
      }
      return;
    }
    if (event.altKey && event.key.toLowerCase() === "n") {
      event.preventDefault();
      emit(this, "navigate", "/new");
    }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "b") {
      event.preventDefault();
      this.sidebarOpen = !this.sidebarOpen;
    }
  };
  private menu(id: string): void {
    this.selectedId = id;
    this.deckTitle =
      this.sessions.list().data?.items.find((session) => session.id === id)?.title ?? "";
    this.error = "";
    this.renderRoot.querySelector<HTMLDialogElement>("#session-actions")?.showModal();
  }
  private async action(operation: "rename" | "star" | "delete"): Promise<void> {
    if (this.sessions.busy) {
      return;
    }
    this.error = "";
    const id = this.selectedId;
    try {
      if (operation === "rename") {
        if (!this.deckTitle.trim()) {
          return;
        }
        await this.sessions.rename.mutateAsync([id, { title: this.deckTitle.trim() }]);
      }
      if (operation === "star") {
        const starred = this.sessions
          .list()
          .data?.items.find((session) => session.id === id)?.isStarred;
        await (starred ? this.sessions.unstar : this.sessions.star).mutateAsync(id);
      }
      if (operation === "delete") {
        await this.sessions.remove.mutateAsync(id);
        if (sessionIdFromPath(this.path) === id) {
          emit(this, "navigate", "/new");
        }
      }
      await this.sessions.refresh();
      this.renderRoot.querySelector<HTMLDialogElement>("#session-actions")?.close();
    } catch (error) {
      this.error = errorMessage(error);
    }
  }
  static styles = css`
    ${pageStyles}
    :host {
      display: block;
      height: 100dvh;
    }
    .shell {
      display: flex;
      height: 100%;
    }
    side-bar {
      width: 252px;
      flex: 0 0 252px;
      border-right: 1px solid var(--color-border);
    }
    main {
      display: flex;
      flex-direction: column;
      min-width: 0;
      flex: 1;
      min-height: 0;
    }
    .topbar {
      display: flex;
      align-items: center;
      height: 58px;
      flex-shrink: 0;
      gap: 12px;
      padding: 0 24px;
      border-bottom: 1px solid var(--color-border);
    }
    .topbar app-breadcrumb {
      flex: 1;
    }
    .studio-status {
      display: flex;
      align-items: center;
      gap: 7px;
      color: var(--color-muted);
      font-size: 10px;
    }
    .dot {
      width: 5px;
      height: 5px;
      border-radius: 50%;
      background: var(--color-accent);
    }
    chat-page {
      flex: 1;
      min-height: 0;
    }
    library-page,
    settings-page {
      flex: 1;
      min-height: 0;
    }
    .scrim {
      display: none;
    }
    .danger {
      color: var(--color-error);
    }
    ol {
      padding-left: 20px;
      color: var(--color-muted);
      font-size: 13px;
      line-height: 1.9;
    }
    @media (max-width: 800px) {
      side-bar {
        position: fixed;
        inset: 0 auto 0 0;
        width: min(285px, 88vw);
        z-index: 30;
      }
      .scrim {
        display: block;
        position: fixed;
        inset: 0;
        background: #0009;
        border: 0;
        z-index: 29;
      }
      .topbar {
        padding-inline: 18px;
      }
    }
  `;
  render() {
    const list = this.sessions.list();
    const sessions = list.data?.items ?? [];
    const id = sessionIdFromPath(this.path) ?? "";
    const isChat = this.path === "/new" || !!id;
    const selected = sessions.find((session) => session.id === this.selectedId);
    const listError = list.isError ? "Deine Sammlung konnte nicht geladen werden." : "";
    return html`<div
        class="shell"
        @session-select=${(event: CustomEvent<string>) => emit(this, "navigate", chatPath(event.detail))}
        @session-menu=${(event: CustomEvent<string>) => this.menu(event.detail)}
        @sessions-retry=${() => this.sessions.refresh()}
      >
        ${this.sidebarOpen ? html`<button class="scrim" aria-label="Navigation schließen" @click=${() => (this.sidebarOpen = false)}></button><side-bar .entries=${sessions.map((session) => ({ id: session.id, title: session.title, starred: session.isStarred }))} .activeId=${id} .path=${this.path} .userName=${this.user.name} ?loading=${list.isPending} .error=${listError} @sidebar-toggle=${() => (this.sidebarOpen = false)} @show-rules=${() => this.renderRoot.querySelector<HTMLDialogElement>("#rules")?.showModal()}></side-bar>` : nothing}
        <main>
          ${
            !isChat
              ? html`<div class="topbar">
                  ${!this.sidebarOpen ? html`<button class="icon-button" aria-label="Seitenleiste öffnen" @click=${() => (this.sidebarOpen = true)}>${icon("panelLeft", 18)}</button>` : nothing}<app-breadcrumb
                    label="Seitennavigation"
                    .items=${[{ label: "Dein Deckstudio" }, { label: this.path === "/settings" ? "Einstellungen" : this.path === "/decks" ? "Meine Decks" : "Musik & Erinnerungen" }]}
                  ></app-breadcrumb
                  ><span class="studio-status"><span class="dot"></span> Made for game night</span>
                </div>`
              : nothing
          }
          ${
            this.path === "/settings"
              ? html`<settings-page .user=${this.user}></settings-page>`
              : this.path === "/decks"
                ? html`<library-page
                    .sessions=${sessions}
                    ?loading=${list.isPending}
                    .error=${listError}
                  ></library-page>`
                : this.path === "/new" || id
                  ? html`<chat-page
                      .sessionId=${id}
                      .user=${this.user}
                      .sidebarOpen=${this.sidebarOpen}
                      @open-sidebar=${() => (this.sidebarOpen = true)}
                      @session-created=${(event: CustomEvent<string>) => emit(this, "navigate", chatPath(event.detail))}
                      @session-changed=${() => this.sessions.refresh()}
                    ></chat-page>`
                  : html`<div class="status">
                      <h1>Diese Seite gibt es nicht.</h1>
                      <button class="button" @click=${() => emit(this, "navigate", "/new")}>
                        Zum Deckstudio
                      </button>
                    </div>`
          }
        </main>
      </div>
      <dialog id="session-actions" aria-label="Deck verwalten">
        <h2>Dein Deck</h2>
        <form
          @submit=${(event: Event) => {
            event.preventDefault();
            void this.action("rename");
          }}
        >
          <label class="field"
            >Name<input
              class="input"
              aria-label="Deckname"
              maxlength="120"
              required
              .value=${this.deckTitle}
              @input=${(event: Event) => (this.deckTitle = (event.target as HTMLInputElement).value)} /></label
          >${this.error ? html`<p class="error" role="alert">${this.error}</p>` : nothing}
          <div class="actions">
            <button
              class="button"
              type="button"
              ?disabled=${this.sessions.busy}
              @click=${() => this.action("star")}
            >
              ${selected?.isStarred ? "Aus Favoriten entfernen" : "Als Favorit speichern"}</button
            ><button
              class="button primary"
              ?disabled=${this.sessions.busy || !this.deckTitle.trim()}
            >
              Speichern
            </button>
          </div>
        </form>
        <details style="margin-top: 24px">
          <summary class="danger">Deck löschen</summary>
          <p>Das Deck und seine Unterhaltung werden dauerhaft gelöscht.</p>
          <button
            class="button danger"
            ?disabled=${this.sessions.busy}
            @click=${() => this.action("delete")}
          >
            Endgültig löschen
          </button>
        </details>
        <div class="actions">
          <button
            class="text-button"
            @click=${() => this.renderRoot.querySelector<HTMLDialogElement>("#session-actions")?.close()}
          >
            Schließen
          </button>
        </div>
      </dialog>
      <dialog id="rules" aria-label="Spielidee">
        <h2>Ein Song. Ein Jahr. Dein Moment.</h2>
        <p>So wird aus deinem Deck ein Musikquiz:</p>
        <ol>
          <li>Erstelle dein Deck und lade die Karten als PDF herunter.</li>
          <li>Drucke die Karten aus und schneide sie entlang der Markierungen aus.</li>
          <li>Scanne den Musik-QR-Code einer verdeckten Karte und höre den Song.</li>
          <li>Ordne ihn auf deiner Zeitleiste ein. Erst dann wird das Jahr aufgedeckt.</li>
          <li>Legt gemeinsam fest, wie viele richtig eingeordnete Karten zum Sieg führen.</li>
        </ol>
        <div class="actions">
          <button
            class="button primary"
            @click=${() => this.renderRoot.querySelector<HTMLDialogElement>("#rules")?.close()}
          >
            Ab an den Spieltisch
          </button>
        </div>
      </dialog>`;
  }
}
