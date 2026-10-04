import { msg, localized } from "@lit/localize";
import { css, html, LitElement } from "lit";
import { customElement, property } from "lit/decorators.js";
import { workspaceStyles } from "@shared/styles/workspace";
import { icon } from "@shared/ui/icons";
import "@chat";
import "@features/deck/components/music-card";
import { starters, exampleCards } from "./examples";

@customElement("studio-page")
@localized()
export class StudioPage extends LitElement {
  @property() draft = "";
  @property({ type: Boolean }) pending = false;
  private select(prompt: string): void {
    this.dispatchEvent(
      new CustomEvent("draft-change", { detail: prompt, bubbles: true, composed: true }),
    );
    this.querySelector<import("@chat").ChatComposer>("chat-composer")?.focusInput();
  }
  static styles = css`
    ${workspaceStyles}
    :host {
      display: block;
      height: 100%;
      overflow-y: auto;
    }
    .content {
      width: min(100%, 760px);
      margin: 0 auto;
      padding: clamp(22px, 5vh, 65px) 28px 32px;
    }
    .hero {
      text-align: center;
    }
    .cards {
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;
      height: 215px;
      margin-bottom: 24px;
    }
    music-card {
      width: 137px;
      position: relative;
    }
    music-card:first-child {
      transform: rotate(-14deg) translate(21px, 9px);
    }
    music-card:nth-child(2) {
      z-index: 2;
      transform: translateY(-8px);
    }
    music-card:last-child {
      transform: rotate(14deg) translate(-21px, 9px);
    }
    .eyebrow {
      margin: 0 0 13px;
      font-size: 10px;
      letter-spacing: 2px;
    }
    h1 {
      margin: 0;
      font-size: clamp(27px, 3.5vw, 38px);
      font-weight: 500;
      line-height: 1.2;
      letter-spacing: -1.7px;
    }
    .intro {
      margin: 14px auto 29px;
      max-width: 470px;
      font-size: 14px;
      color: var(--color-muted);
      line-height: 1.7;
      text-wrap: balance;
    }
    .suggestion-label {
      margin: 26px 0 12px;
      font-size: 11px;
      color: var(--color-muted);
    }
    .starters {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }
    .starter {
      padding: 16px 13px;
      text-align: left;
      border: 1px solid var(--color-border);
      border-radius: 12px;
      background: transparent;
      color: var(--color-text);
      transition:
        background 0.15s,
        border-color 0.15s;
    }
    .starter:hover {
      background: var(--color-sidebar);
      border-color: var(--color-border-strong);
    }
    .starter svg {
      color: var(--color-muted);
      margin-bottom: 9px;
    }
    strong {
      display: block;
      font-size: 12px;
      font-weight: 500;
    }
    .starter span {
      display: block;
      margin-top: 5px;
      color: var(--color-muted);
      font-size: 10px;
      line-height: 1.6;
    }
    .hint {
      text-align: center;
      margin: 24px 0 0;
      font-size: 10px;
      color: var(--color-muted);
    }
    @media (max-width: 550px) {
      .content {
        padding: 24px 20px;
      }
      .cards {
        height: 173px;
        margin-bottom: 18px;
      }
      music-card {
        width: 111px;
      }
      .starters {
        grid-template-columns: 1fr;
        gap: 8px;
      }
      .starter {
        display: grid;
        grid-template-columns: 20px 1fr;
        gap: 0 10px;
        padding: 12px;
      }
      .starter svg {
        grid-row: span 2;
        margin: 3px 0 0;
      }
      .starter span {
        margin-top: 2px;
      }
      h1 {
        font-size: 29px;
      }
    }
  `;
  render() {
    return html`<div class="content">
      <section class="hero" aria-labelledby="welcome-title">
        <div class="cards" aria-label=${msg("Beispielkarten")}>
          ${exampleCards.map((card, i) => html`<music-card .card=${card} .index=${i}></music-card>`)}
        </div>
        <p class="eyebrow">${msg("GUTE MUSIK. GUTE LEUTE. DEIN DECK.")}</p>
        <h1 id="welcome-title">
          ${msg("Jeder Hit hat seine Zeit.")}<br />${msg("Welche ist deine?")}
        </h1>
        <p class="intro">
          ${msg("Mach aus deinen Lieblingssongs ein eigenes Kartenspiel.")}<br />${msg("Du bringst die Idee. Hier entsteht dein Deck.")}
        </p>
      </section>
      <slot></slot>
      <p class="suggestion-label">${msg("Ein bisschen Inspiration für den Anfang")}</p>
      <div class="starters">
        ${starters().map((starter) => html`<button class="starter" ?disabled=${this.pending} @click=${() => this.select(starter.prompt)}>${icon(starter.icon, 18)}<strong>${starter.title}</strong><span>${starter.description}</span></button>`)}
      </div>
      <p class="hint">${msg("Für deinen nächsten Spieleabend. Mit Musik, die euch verbindet.")}</p>
    </div>`;
  }
}
