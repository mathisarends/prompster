import { msg, localized, str } from "@lit/localize";
import { getLocale } from "@shared/i18n";
import { shortcutKeys, shortcutTitle } from "@shared/shortcuts";
import { css, html, LitElement, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { pageStyles } from "@shared/styles/page";
import { icon } from "@shared/ui/icons";
import { emit } from "@shared/events";
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
  @state() private collapsed = new Set<string>();
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
      padding: 0 8px 10px;
    }
    .icon-button {
      width: 28px;
      height: 28px;
      border-radius: var(--radius-sm);
      color: var(--color-muted);
    }
    header {
      display: flex;
      align-items: center;
      gap: 8px;
      height: 52px;
      flex-shrink: 0;
      padding: 0 4px;
    }
    .brand {
      font-size: var(--font-size-body);
      font-weight: var(--font-weight-semibold);
      letter-spacing: -0.01em;
    }
    .search {
      display: flex;
      align-items: center;
      gap: 4px;
      height: 32px;
      margin: 2px 0 6px;
      padding: 0 2px 0 10px;
      border-radius: var(--radius-control);
      color: var(--color-muted);
    }
    .search:focus-within {
      background: var(--color-surface);
    }
    .search input {
      flex: 1;
      min-width: 0;
      padding: 6px;
      border: 0;
      outline: none;
      box-shadow: none;
      background: transparent;
      color: var(--color-text);
      font-size: var(--font-size-body);
    }
    .search input::placeholder {
      color: var(--color-muted);
    }
    .search input::-webkit-search-cancel-button {
      display: none;
    }
    .decks {
      flex: 1;
      min-height: 0;
      overflow-y: auto;
    }
    .group {
      display: flex;
      align-items: center;
      gap: 6px;
      width: 100%;
      height: 28px;
      margin-top: 10px;
      padding: 0 10px;
      border: 0;
      border-radius: var(--radius-sm);
      background: none;
      color: var(--color-faint);
      font-size: var(--font-size-caption);
      font-weight: var(--font-weight-medium);
      text-align: left;
    }
    .group:hover {
      color: var(--color-muted);
    }
    .group .count {
      margin-left: auto;
      font-weight: var(--font-weight-regular);
      font-variant-numeric: tabular-nums;
    }
    .group svg {
      transition: transform 0.15s;
    }
    .group[aria-expanded="true"] svg {
      transform: rotate(90deg);
    }
    .row {
      position: relative;
      margin-bottom: 1px;
      border-radius: var(--radius-sm);
    }
    .row:hover {
      background: var(--color-hover);
    }
    .row.active {
      background: var(--color-active);
    }
    .open {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      align-items: center;
      gap: 9px;
      width: 100%;
      min-height: 32px;
      padding: 6px 10px;
      border: 0;
      border-radius: inherit;
      background: none;
      color: var(--color-muted);
      text-align: left;
    }
    .title {
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
      font-size: var(--font-size-label);
    }
    .row:hover .title,
    .row.active .title {
      color: var(--color-text);
    }
    .pin {
      display: flex;
      color: var(--color-faint);
    }
    .row .icon-button {
      position: absolute;
      top: 50%;
      right: 4px;
      width: 24px;
      height: 24px;
      transform: translateY(-50%);
      background: var(--color-raised);
      opacity: 0;
    }
    .row:hover .icon-button,
    .row:focus-within .icon-button {
      opacity: 1;
    }
    .empty {
      margin: 8px 10px;
      color: var(--color-faint);
      font-size: var(--font-size-label);
      line-height: 1.7;
    }
    footer {
      display: flex;
      align-items: center;
      gap: 2px;
      padding: 8px 2px 0;
    }
    footer .icon-button.active {
      color: var(--color-text);
      background: var(--color-chip);
    }
    .avatar {
      display: grid;
      place-items: center;
      width: 24px;
      height: 24px;
      margin-left: auto;
      margin-right: 4px;
      padding: 0;
      border: 0;
      border-radius: 50%;
      background: var(--color-control);
      color: var(--color-text);
      font-size: var(--font-size-micro);
      font-weight: var(--font-weight-medium);
    }
    .avatar:hover,
    .avatar.active {
      background: var(--color-control-hover);
    }
    @media (hover: none) {
      .row .icon-button {
        opacity: 1;
        background: none;
        color: var(--color-faint);
      }
      .pin {
        visibility: hidden;
      }
    }
  `;
  private row(entry: SidebarEntry) {
    const title = entry.title || msg("Neues Deck");
    return html`<div class="row ${this.activeId === entry.id ? "active" : ""}">
      <button
        class="open"
        aria-label=${title}
        aria-current=${this.activeId === entry.id ? "page" : nothing}
        @click=${() => emit(this, "session-select", entry.id)}
      >
        <span class="title">${title}</span
        >${entry.starred ? html`<span class="pin">${icon("star", 12, true)}</span>` : nothing}</button
      ><button
        class="icon-button"
        aria-label=${msg(str`Aktionen für ${title}`)}
        title=${msg(str`Aktionen für ${title}`)}
        @click=${() => emit(this, "session-menu", entry.id)}
      >
        ${icon("more", 14)}
      </button>
    </div>`;
  }
  private group(id: string, label: string, entries: SidebarEntry[]) {
    if (!entries.length) {
      return nothing;
    }
    const open = !this.collapsed.has(id);
    return html`<button
        class="group"
        aria-expanded=${open}
        @click=${() => {
          const next = new Set(this.collapsed);
          if (open) {
            next.add(id);
          } else {
            next.delete(id);
          }
          this.collapsed = next;
        }}
      >
        ${label}<span class="count">${entries.length}</span>${icon("right", 12)}
      </button>
      ${open ? entries.map((entry) => this.row(entry)) : nothing}`;
  }
  render() {
    const entries = this.entries.filter((entry) =>
      entry.title
        .toLocaleLowerCase(getLocale())
        .includes(this.search.toLocaleLowerCase(getLocale())),
    );
    return html`<aside aria-label=${msg("Hauptnavigation")}>
      <header>
        <button
          class="icon-button"
          aria-label=${msg("Seitenleiste schließen")}
          title=${shortcutTitle(msg("Seitenleiste schließen"), "sidebar")}
          aria-keyshortcuts=${shortcutKeys("sidebar")}
          @click=${() => emit(this, "sidebar-toggle")}
        >
          ${icon("panelLeft", 16)}</button
        ><span class="brand">prompster</span>
      </header>
      <label class="search"
        >${icon("search", 15)}<input
          type="search"
          aria-label=${msg("Decks durchsuchen")}
          placeholder=${msg("Suchen")}
          .value=${this.search}
          @input=${(event: Event) => (this.search = (event.target as HTMLInputElement).value)}
        /><button
          class="icon-button"
          aria-label=${msg("Neues Deck")}
          title=${shortcutTitle(msg("Neues Deck"), "newDeck")}
          aria-keyshortcuts=${shortcutKeys("newDeck")}
          @click=${() => emit(this, "navigate", "/new")}
        >
          ${icon("compose", 15)}
        </button></label
      >
      <div class="decks">
        ${this.loading ? html`<p class="empty" role="status">${msg("Sammlung wird geladen …")}</p>` : nothing}${this.error ? html`<p class="empty" role="alert">${this.error} <button class="text-button" @click=${() => emit(this, "sessions-retry")}>${msg("Erneut versuchen")}</button></p>` : nothing}
        ${this.group(
          "starred",
          msg("Favoriten"),
          entries.filter((entry) => entry.starred),
        )}
        ${this.group(
          "decks",
          msg("Decks"),
          entries.filter((entry) => !entry.starred),
        )}
        ${!entries.length && !this.loading && !this.error ? html`<p class="empty">${this.search ? msg("Keine passenden Decks.") : msg("Hier ist Platz für deine nächsten Lieblingsdecks.")}</p>` : nothing}
      </div>
      <footer>
        <button
          class="icon-button ${this.path === "/settings" ? "active" : ""}"
          aria-label=${msg("Einstellungen")}
          title=${shortcutTitle(msg("Einstellungen"), "settings")}
          aria-keyshortcuts=${shortcutKeys("settings")}
          @click=${() => emit(this, "navigate", "/settings")}
        >
          ${icon("settings", 16)}</button
        ><button
          class="icon-button ${this.path === "/decks" ? "active" : ""}"
          aria-label=${msg("Meine Decks")}
          title=${msg("Meine Decks")}
          @click=${() => emit(this, "navigate", "/decks")}
        >
          ${icon("layers", 16)}</button
        ><button
          class="avatar ${this.path === "/settings" ? "active" : ""}"
          aria-label=${msg(str`${this.userName} · Konto und Einstellungen`)}
          title=${this.userName}
          @click=${() => emit(this, "navigate", "/settings")}
        >
          ${this.userName.slice(0, 1).toLocaleUpperCase(getLocale())}
        </button>
      </footer>
    </aside>`;
  }
}
