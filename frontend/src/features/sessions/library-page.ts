import { css, html, LitElement, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { SessionSummaryResponse } from "@api/generated/sessions";
import { pageStyles } from "@shared/styles/page";
import { icon } from "@shared/ui/icons";
import { emit } from "@shared/events";

@customElement("library-page")
export class LibraryPage extends LitElement {
  @property({ attribute: false }) sessions: SessionSummaryResponse[] = [];
  @property({ type: Boolean }) loading = false;
  @property() error = "";
  @state() private filter = "";
  static styles = css`
    ${pageStyles} :host {
      display: block;
      padding: 40px clamp(20px, 5vw, 72px);
      overflow-y: auto;
    }
    header {
      display: flex;
      gap: 20px;
      justify-content: space-between;
      align-items: center;
    }
    h1 {
      font-size: 30px;
      margin: 0;
    }
    header p {
      color: var(--color-muted);
      font-size: 13px;
    }
    .input {
      margin: 22px 0;
      max-width: 380px;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
      gap: 18px;
    }
    .tile {
      position: relative;
      padding: 22px;
      border: 1px solid var(--color-border);
      border-radius: 16px;
      background: var(--color-sidebar);
      color: var(--color-text);
      text-align: left;
    }
    .tile:hover {
      background: var(--color-panel);
    }
    .art {
      width: 60px;
      height: 76px;
      display: grid;
      place-items: center;
      border-radius: 9px;
      background: var(--color-card-lime);
      color: var(--color-card-ink);
      transform: rotate(-8deg);
      margin: 4px 0 26px;
    }
    .tile:nth-child(3n + 2) .art {
      background: var(--color-card-lilac);
    }
    .tile:nth-child(3n) .art {
      background: var(--color-card-peach);
    }
    .title {
      display: block;
      font-size: 14px;
      overflow-wrap: anywhere;
    }
    small {
      display: block;
      font-size: 11px;
      margin-top: 8px;
      color: var(--color-muted);
    }
    .star {
      position: absolute;
      right: 22px;
      top: 22px;
      color: var(--color-accent);
    }
  `;
  render() {
    const sessions = this.sessions.filter((item) =>
      item.title.toLowerCase().includes(this.filter.toLowerCase()),
    );
    return html`<header>
        <div>
          <p class="eyebrow">DEINE MUSIK. DEINE ERINNERUNGEN.</p>
          <h1>Meine Decks</h1>
          <p>Für die nächste Runde ist immer Platz.</p>
        </div>
        <button class="button primary" @click=${() => emit(this, "navigate", "/new")}>
          ${icon("plus", 16)} Neues Deck
        </button>
      </header>
      <input
        class="input"
        type="search"
        aria-label="Sammlung filtern"
        placeholder="Dein nächster Lieblingsmix …"
        .value=${this.filter}
        @input=${(event: Event) => (this.filter = (event.target as HTMLInputElement).value)}
      />${this.loading ? html`<p class="status" role="status">Decks werden geladen …</p>` : nothing}${this.error ? html`<p class="error" role="alert">${this.error}<button class="text-button" @click=${() => emit(this, "sessions-retry")}>Erneut versuchen</button></p>` : nothing}
      <div class="grid">
        ${sessions.map((session) => html`<button class="tile" @click=${() => emit(this, "session-select", session.id)}><span class="art">${icon("music", 28)}</span>${session.isStarred ? html`<span class="star">${icon("sparkles", 16)}</span>` : nothing}<strong class="title">${session.title || "Neues Deck"}</strong><small>${new Intl.DateTimeFormat("de", { day: "numeric", month: "long", year: "numeric" }).format(new Date(session.lastActivityAt))}</small></button>`)}
      </div>
      ${!sessions.length && !this.loading && !this.error ? html`<div class="status"><p>${this.filter ? "Kein Deck passt zu deiner Suche." : "Deine Sammlung beginnt mit einer Idee."}</p></div>` : nothing}`;
  }
}
