import { css, html, LitElement } from "lit";
import { customElement, property } from "lit/decorators.js";
import { workspaceStyles } from "@shared/styles/workspace";
import { icon } from "@shared/ui/icons";
export type SongCard = { id: string; title: string; artist: string; year: number };

@customElement("music-card")
export class MusicCard extends LitElement {
  @property({ attribute: false }) card?: SongCard;
  @property() tone: "lime" | "lilac" | "peach" = "lime";
  @property({ type: Boolean }) concealed = false;
  static styles = css`
    ${workspaceStyles}
    :host {
      display: block;
    }
    article {
      aspect-ratio: 3 / 4;
      display: flex;
      flex-direction: column;
      padding: 18px;
      border-radius: 14px;
      color: var(--color-card-ink);
      background: var(--color-card-lime);
      overflow: hidden;
      box-shadow: 0 8px 25px #0002;
    }
    .lilac {
      background: var(--color-card-lilac);
    }
    .peach {
      background: var(--color-card-peach);
    }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 9px;
      font-weight: 500;
      letter-spacing: 1px;
    }
    .record {
      display: grid;
      place-items: center;
      align-self: center;
      width: 57%;
      aspect-ratio: 1;
      margin: auto 0;
      border: 1px solid currentColor;
      border-radius: 50%;
      background: repeating-radial-gradient(circle, transparent 0 9px, #22261d13 10px 11px);
    }
    .record svg {
      padding: 9px;
      width: 38px;
      height: 38px;
      border-radius: 50%;
      color: var(--color-card-lime);
      background: var(--color-card-ink);
    }
    .year {
      font: 500 clamp(30px, 4vw, 42px) var(--font-sans);
      letter-spacing: -2px;
      line-height: 1.1;
    }
    h3 {
      margin: 8px 0 3px;
      font-size: 12px;
      letter-spacing: -0.3px;
      line-height: 1.3;
      overflow-wrap: anywhere;
    }
    p {
      margin: 0;
      font-size: 10px;
    }
    .hidden-year {
      text-align: center;
      margin: auto 0;
      font: 500 60px var(--font-sans);
    }
  `;
  render() {
    if (!this.card) {
      return html``;
    }
    return html`<article
      class=${this.tone}
      aria-label=${this.concealed ? "Verdeckte Musik-Karte" : `${this.card.title}, ${this.card.artist}, ${this.card.year}`}
    >
      <header><span>PROMPSTER</span>${icon("music", 13)}</header>
      ${
        this.concealed
          ? html`<div class="hidden-year">?</div>
              <p>Welches Jahr war das?</p>`
          : html`<div class="record">${icon("music", 18)}</div>
              <div class="year">${this.card.year}</div>
              <h3>${this.card.title}</h3>
              <p>${this.card.artist}</p>`
      }
    </article>`;
  }
}
