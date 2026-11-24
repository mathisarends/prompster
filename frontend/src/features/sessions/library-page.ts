import { msg, localized } from "@lit/localize";
import { formatDate, getLocale } from "@shared/i18n";
import { css, html, LitElement, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { SessionSummaryResponse } from "@api/generated/sessions";
import { pageStyles } from "@shared/styles/page";
import { icon } from "@shared/ui/icons";
import { emit } from "@shared/events";
import "@shared/ui/deck-cover";

@customElement("library-page")
@localized()
export class LibraryPage extends LitElement {
  @property({ attribute: false }) sessions: SessionSummaryResponse[] = [];
  @property({ type: Boolean }) loading = false;
  @property() error = "";
  @state() private filter = "";
  static styles = css`
    ${pageStyles}
    :host {
      display: block;
      overflow-y: auto;
    }
    .page {
      width: min(100%, var(--content-width));
      margin: 0 auto;
      padding: 56px 24px 64px;
    }
    header {
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 20px;
      margin-bottom: 24px;
    }
    h1 {
      margin: 0;
      font-size: var(--font-size-title);
    }
    header p {
      margin: 4px 0 0;
      color: var(--color-muted);
    }
    .filter {
      display: flex;
      align-items: center;
      gap: 8px;
      height: 40px;
      margin-bottom: 12px;
      padding: 0 12px;
      border: 1px solid var(--color-border);
      border-radius: var(--radius-control);
      background: var(--color-surface);
      color: var(--color-faint);
    }
    .filter:focus-within {
      border-color: var(--color-border-strong);
    }
    .filter input {
      flex: 1;
      min-width: 0;
      border: 0;
      outline: none;
      background: transparent;
      color: var(--color-text);
      font: inherit;
    }
    .filter input::placeholder {
      color: var(--color-faint);
    }
    ul {
      margin: 0;
      padding: 0;
      list-style: none;
    }
    .deck {
      display: flex;
      align-items: center;
      gap: 12px;
      width: 100%;
      height: 64px;
      padding: 0 8px;
      border: 0;
      border-radius: var(--radius-xs);
      background: none;
      color: var(--color-text);
      text-align: left;
    }
    .deck:hover {
      background: var(--color-row-hover);
    }
    deck-cover {
      width: 48px;
      flex-shrink: 0;
    }
    .meta {
      flex: 1;
      min-width: 0;
      line-height: 1.35;
    }
    .title,
    .subtitle {
      display: block;
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
    }
    .title {
      color: var(--color-text-strong);
      font-size: var(--font-size-track);
    }
    .subtitle {
      display: flex;
      align-items: center;
      gap: 6px;
      color: var(--color-muted);
      font-size: var(--font-size-label);
    }
    .subtitle svg {
      flex-shrink: 0;
      color: var(--color-play);
    }
    @media (max-width: 560px) {
      .page {
        padding: 32px 16px 48px;
      }
      header {
        align-items: center;
      }
      header p {
        display: none;
      }
    }
  `;
  render() {
    const query = this.filter.toLocaleLowerCase(getLocale());
    const sessions = this.sessions.filter((item) =>
      item.title.toLocaleLowerCase(getLocale()).includes(query),
    );
    return html`<div class="page">
      <header>
        <div>
          <h1>${msg("Meine Decks")}</h1>
          <p>${msg("Für die nächste Runde ist immer Platz.")}</p>
        </div>
        <button class="button primary" @click=${() => emit(this, "navigate", "/new")}>
          ${icon("plus", 16)} ${msg("Neues Deck")}
        </button>
      </header>
      <label class="filter">
        ${icon("search", 16)}
        <input
          type="search"
          aria-label=${msg("Sammlung filtern")}
          placeholder=${msg("Dein nächster Lieblingsmix …")}
          .value=${this.filter}
          @input=${(event: Event) => (this.filter = (event.target as HTMLInputElement).value)}
        />
      </label>
      ${this.loading ? html`<p class="status" role="status">${msg("Decks werden geladen …")}</p>` : nothing}
      ${
        this.error
          ? html`<p class="error" role="alert">
              ${this.error}
              <button class="text-button" @click=${() => emit(this, "sessions-retry")}>
                ${msg("Erneut versuchen")}
              </button>
            </p>`
          : nothing
      }
      <ul>
        ${sessions.map((session) => {
          const title = session.title || msg("Neues Deck");
          return html`<li>
            <button
              class="deck"
              aria-label=${title}
              @click=${() => emit(this, "session-select", session.id)}
            >
              <deck-cover .urls=${session.coverUrls ?? []}></deck-cover>
              <span class="meta">
                <span class="title">${title}</span>
                <span class="subtitle">
                  ${session.isStarred ? html`<span role="img" aria-label=${msg("Favorit")}>${icon("star", 12, true)}</span>` : nothing}
                  ${msg("Deck")} ·
                  <time datetime=${session.lastActivityAt}
                    >${formatDate(session.lastActivityAt)}</time
                  >
                </span>
              </span>
            </button>
          </li>`;
        })}
      </ul>
      ${
        !sessions.length && !this.loading && !this.error
          ? html`<div class="status">
              ${icon("layers", 24)}
              <p>
                ${this.filter ? msg("Kein Deck passt zu deiner Suche.") : msg("Deine Sammlung beginnt mit einer Idee.")}
              </p>
            </div>`
          : nothing
      }
    </div>`;
  }
}
