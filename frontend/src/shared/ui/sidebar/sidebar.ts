import { msg, localized, str } from "@lit/localize";
import { getLocale } from "@shared/i18n";
import { shortcutKeys, shortcutTitle } from "@shared/shortcuts";
import { css, html, LitElement, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { pageStyles } from "@shared/styles/page";
import { icon } from "@shared/ui/icons";
import { emit } from "@shared/events";
import "@shared/ui/brand-mark";
import type { SidebarEntry } from "./types";

@customElement("side-bar")
@localized()
export class Sidebar extends LitElement {
  @property({ attribute: false }) entries: SidebarEntry[] = [];
  @property() activeId = "";
  @property() path = "";
  @property() userName = "";
  @property({ type: Boolean }) loading = false;
  @property() error = "";
  @state() private search = "";
  static styles = css`
    ${pageStyles}
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
      background: var(--color-sidebar);
    }
    aside {
      display: flex;
      flex-direction: column;
      height: 100%;
      padding: 0 14px 16px;
    }
    header {
      height: 82px;
      flex-shrink: 0;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding-left: 10px;
    }
    .nav {
      display: flex;
      align-items: center;
      gap: 11px;
      min-height: 43px;
      width: 100%;
      padding: 9px 12px;
      border: 0;
      border-radius: 9px;
      background: transparent;
      color: var(--color-muted);
      text-align: left;
      text-decoration: none;
    }
    .nav:hover,
    .nav.active,
    .row.active {
      color: var(--color-text);
      background: var(--color-panel);
    }
    .new {
      margin: 12px 0 8px;
      color: var(--color-text);
      border: 1px solid var(--color-border);
    }
    .new svg {
      color: var(--color-accent);
    }
    .nav kbd {
      margin-left: auto;
      font: 10px var(--font-sans);
      opacity: 0.6;
    }
    .group {
      margin: 22px 12px 9px;
      font-size: 10px;
      letter-spacing: 0.05em;
      color: var(--color-muted);
    }
    .decks {
      min-height: 0;
      overflow-y: auto;
      flex: 1;
    }
    .row {
      display: flex;
      align-items: center;
      border-radius: 9px;
    }
    .row .nav {
      font-size: 12px;
      gap: 9px;
      flex: 1;
      min-width: 0;
    }
    .row span {
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
    }
    .row .icon-button {
      opacity: 0;
      width: 27px;
      flex-shrink: 0;
    }
    .row:hover .icon-button,
    .row:focus-within .icon-button {
      opacity: 1;
    }
    .empty {
      margin: 12px;
      color: var(--color-muted);
      font-size: 12px;
      line-height: 1.8;
    }
    .search {
      display: flex;
      align-items: center;
      padding: 0 12px;
      color: var(--color-muted);
      margin-top: 16px;
    }
    input {
      min-width: 0;
      width: 100%;
      padding: 10px 8px;
      color: var(--color-text);
      background: transparent;
      border: 0;
      font-size: 12px;
    }
    footer {
      padding-top: 12px;
      border-top: 1px solid var(--color-border);
    }
    .profile {
      margin-top: 12px;
    }
    .avatar {
      width: 30px;
      height: 30px;
      border: 1px solid var(--color-border);
      border-radius: 50%;
      display: grid;
      place-items: center;
      color: var(--color-accent);
      font-size: 12px;
      flex-shrink: 0;
    }
    .profile strong {
      display: block;
      font-size: 12px;
    }
    .profile small {
      display: block;
      font-size: 10px;
      color: var(--color-muted);
    }
    @media (hover: none) {
      .row .icon-button {
        opacity: 1;
      }
    }
  `;
  private row(entry: SidebarEntry) {
    return html`<div class="row ${this.activeId === entry.id ? "active" : ""}">
      <button
        class="nav"
        aria-current=${this.activeId === entry.id ? "page" : nothing}
        @click=${() => emit(this, "session-select", entry.id)}
      >
        ${icon(entry.starred ? "sparkles" : "disc", 15)}<span
          >${entry.title || msg("Neues Deck")}</span
        ></button
      ><button
        class="icon-button"
        aria-label=${msg(str`Aktionen für ${entry.title || msg("Neues Deck")}`)}
        title=${msg(str`Aktionen für ${entry.title || msg("Neues Deck")}`)}
        @click=${() => emit(this, "session-menu", entry.id)}
      >
        ${icon("more", 17)}
      </button>
    </div>`;
  }
  render() {
    const entries = this.entries.filter((entry) =>
      entry.title
        .toLocaleLowerCase(getLocale())
        .includes(this.search.toLocaleLowerCase(getLocale())),
    );
    return html`<aside aria-label=${msg("Hauptnavigation")}>
      <header>
        <brand-mark></brand-mark
        ><button
          class="icon-button"
          aria-label=${msg("Seitenleiste schließen")}
          title=${shortcutTitle(msg("Seitenleiste schließen"), "sidebar")}
          aria-keyshortcuts=${shortcutKeys("sidebar")}
          @click=${() => emit(this, "sidebar-toggle")}
        >
          ${icon("panelLeft", 17)}
        </button>
      </header>
      <nav>
        <button
          class="nav new ${this.path === "/new" ? "active" : ""}"
          title=${shortcutTitle(msg("Neues Deck"), "newDeck")}
          aria-keyshortcuts=${shortcutKeys("newDeck")}
          @click=${() => emit(this, "navigate", "/new")}
        >
          ${icon("plus", 17)} ${msg("Neues Deck")} <kbd>Alt N</kbd></button
        ><button
          class="nav ${this.path === "/decks" ? "active" : ""}"
          @click=${() => emit(this, "navigate", "/decks")}
        >
          ${icon("layers", 17)} ${msg("Meine Decks")}
        </button>
      </nav>
      <label class="search"
        >${icon("search", 15)}<input
          type="search"
          aria-label=${msg("Decks durchsuchen")}
          placeholder=${msg("Decks durchsuchen …")}
          .value=${this.search}
          @input=${(event: Event) => (this.search = (event.target as HTMLInputElement).value)}
      /></label>
      <div class="decks">
        ${this.loading ? html`<p class="empty" role="status">${msg("Sammlung wird geladen …")}</p>` : nothing}${this.error ? html`<p class="empty" role="alert">${this.error}<button class="text-button" @click=${() => emit(this, "sessions-retry")}>${msg("Erneut versuchen")}</button></p>` : nothing}
        ${
          entries.some((entry) => entry.starred)
            ? html`<p class="group">${msg("FAVORITEN")}</p>
                ${entries.filter((entry) => entry.starred).map((entry) => this.row(entry))}`
            : nothing
        }
        <p class="group">${msg("DEINE SAMMLUNG")}</p>
        ${entries.filter((entry) => !entry.starred).map((entry) => this.row(entry))}${!entries.length && !this.loading && !this.error ? html`<p class="empty">${this.search ? msg("Keine passenden Decks.") : msg("Hier ist Platz für deine nächsten Lieblingsdecks.")}</p>` : nothing}
      </div>
      <footer>
        <button
          class="nav profile"
          title=${shortcutTitle(msg("Einstellungen"), "settings")}
          aria-keyshortcuts=${shortcutKeys("settings")}
          @click=${() => emit(this, "navigate", "/settings")}
        >
          <span class="avatar">${this.userName.slice(0, 1).toLocaleUpperCase(getLocale())}</span
          ><span><strong>${this.userName}</strong><small>${msg("Dein Deckstudio")}</small></span>
        </button>
      </footer>
    </aside>`;
  }
}
