import { msg, localized } from "@lit/localize";
import { css, html, LitElement, nothing, type PropertyValues } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { UserMeResponse } from "@api/generated/users";
import { pageStyles } from "@shared/styles/page";
import { icon } from "@shared/ui/icons";
import { emit, errorMessage } from "@shared/events";
import { matchesShortcut, shortcutKeys, shortcutTitle } from "@shared/shortcuts";
import { SessionsController } from "@features/sessions/sessions-controller";
import { chatPath, sessionIdFromPath } from "./routes";
import "@shared/ui/sidebar";
import "@shared/ui/breadcrumb";
import "@features/chat/chat-page";
import "@features/sessions/library-page";
import "@features/settings/settings-page";

@customElement("app-layout")
@localized()
export class AppLayout extends LitElement {
  @property() path = "/new";
  @property({ attribute: false }) user!: UserMeResponse;
  @state() private sidebarOpen = window.innerWidth > 800;
  @state() private selectedId = "";
  @state() private deckTitle = "";
  @state() private error = "";
  private sessions = new SessionsController(this);
  // Keep the connected studio while visiting settings so locale updates reach
  // its components and drafts, attachments, streams and deck tabs stay intact.
  private retainedSessionId: string | null = null;
  connectedCallback(): void {
    super.connectedCallback();
    window.addEventListener("keydown", this.keydown);
  }
  disconnectedCallback(): void {
    window.removeEventListener("keydown", this.keydown);
    super.disconnectedCallback();
  }
  protected willUpdate(changed: PropertyValues): void {
    document.title = `${this.path === "/decks" ? msg("Meine Decks") : this.path === "/settings" ? msg("Einstellungen") : msg("Deckstudio")} · Prompster`;
    if (changed.has("path")) {
      const id = sessionIdFromPath(this.path);
      if (this.path === "/new" || id) {
        this.retainedSessionId = id ?? "";
      } else if (this.path !== "/settings") {
        this.retainedSessionId = null;
      }
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
    if (matchesShortcut(event, "newDeck")) {
      event.preventDefault();
      emit(this, "navigate", "/new");
    }
    if (matchesShortcut(event, "sidebar")) {
      event.preventDefault();
      this.sidebarOpen = !this.sidebarOpen;
    }
    if (matchesShortcut(event, "settings")) {
      event.preventDefault();
      emit(this, "navigate", "/settings");
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
      width: var(--sidebar-width);
      flex: 0 0 var(--sidebar-width);
      border-right: 1px solid var(--color-border-subtle);
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
      height: var(--header-height);
      flex-shrink: 0;
      gap: 8px;
      padding: 0 12px 0 16px;
    }
    .topbar app-breadcrumb {
      flex: 1;
    }
    chat-page {
      flex: 1;
      min-height: 0;
    }
    chat-page[hidden] {
      display: none;
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
    dialog details {
      margin-top: 24px;
      padding-top: 16px;
      border-top: 1px solid var(--color-border);
    }
    dialog summary {
      cursor: pointer;
      font-size: var(--font-size-label);
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
        background: var(--color-backdrop);
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
    const listError = list.isError ? msg("Deine Sammlung konnte nicht geladen werden.") : "";
    return html`<div
        class="shell"
        @session-select=${(event: CustomEvent<string>) => emit(this, "navigate", chatPath(event.detail))}
        @session-menu=${(event: CustomEvent<string>) => this.menu(event.detail)}
        @sessions-retry=${() => this.sessions.refresh()}
      >
        ${this.sidebarOpen ? html`<button class="scrim" aria-label=${msg("Navigation schließen")} @click=${() => (this.sidebarOpen = false)}></button><side-bar .entries=${sessions.map((session) => ({ id: session.id, title: session.title, starred: session.isStarred }))} .activeId=${id} .path=${this.path} .userName=${this.user.name} ?loading=${list.isPending} .error=${listError} @sidebar-toggle=${() => (this.sidebarOpen = false)}></side-bar>` : nothing}
        <main>
          ${
            !isChat
              ? html`<div class="topbar">
                  ${!this.sidebarOpen ? html`<button class="icon-button" aria-label=${msg("Seitenleiste öffnen")} title=${shortcutTitle(msg("Seitenleiste öffnen"), "sidebar")} aria-keyshortcuts=${shortcutKeys("sidebar")} @click=${() => (this.sidebarOpen = true)}>${icon("panelLeft", 18)}</button>` : nothing}<app-breadcrumb
                    label=${msg("Seitennavigation")}
                    .items=${[{ label: msg("Deckstudio") }, { label: this.path === "/settings" ? msg("Einstellungen") : this.path === "/decks" ? msg("Meine Decks") : msg("Musik & Erinnerungen") }]}
                  ></app-breadcrumb>
                </div>`
              : nothing
          }
          ${
            this.retainedSessionId !== null
              ? html`<chat-page
                  .sessionId=${this.retainedSessionId}
                  .user=${this.user}
                  .active=${isChat}
                  ?hidden=${!isChat}
                  .sidebarOpen=${this.sidebarOpen}
                  @open-sidebar=${() => (this.sidebarOpen = true)}
                  @session-created=${(event: CustomEvent<string>) => {
                    this.retainedSessionId = event.detail;
                    if (isChat) {
                      emit(this, "navigate", chatPath(event.detail));
                    }
                  }}
                  @session-changed=${() => this.sessions.refresh()}
                ></chat-page>`
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
                : isChat
                  ? nothing
                  : html`<div class="status">
                      <h1>${msg("Diese Seite gibt es nicht.")}</h1>
                      <button class="button" @click=${() => emit(this, "navigate", "/new")}>
                        ${msg("Zum Deckstudio")}
                      </button>
                    </div>`
          }
        </main>
      </div>
      <dialog id="session-actions" aria-label=${msg("Deck verwalten")}>
        <h2>${msg("Dein Deck")}</h2>
        <form
          @submit=${(event: Event) => {
            event.preventDefault();
            void this.action("rename");
          }}
        >
          <label class="field"
            >${msg("Name")}<input
              class="input"
              aria-label=${msg("Deckname")}
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
              ${selected?.isStarred ? msg("Aus Favoriten entfernen") : msg("Als Favorit speichern")}</button
            ><button
              class="button primary"
              ?disabled=${this.sessions.busy || !this.deckTitle.trim()}
            >
              ${msg("Speichern")}
            </button>
          </div>
        </form>
        <details>
          <summary class="danger">${msg("Deck löschen")}</summary>
          <p>${msg("Das Deck und seine Unterhaltung werden dauerhaft gelöscht.")}</p>
          <button
            class="button danger"
            ?disabled=${this.sessions.busy}
            @click=${() => this.action("delete")}
          >
            ${msg("Endgültig löschen")}
          </button>
        </details>
        <div class="actions">
          <button
            class="text-button"
            @click=${() => this.renderRoot.querySelector<HTMLDialogElement>("#session-actions")?.close()}
          >
            ${msg("Schließen")}
          </button>
        </div>
      </dialog>`;
  }
}
