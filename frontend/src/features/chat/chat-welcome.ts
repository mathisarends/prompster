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
    /* Centred like T3's empty thread: a short headline, the composer, suggestions. */
    .content {
      display: flex;
      flex-direction: column;
      justify-content: center;
      width: min(100%, calc(var(--content-width) + 48px));
      min-height: 100%;
      margin: 0 auto;
      padding: 32px 24px 48px;
    }
    .hero {
      text-align: center;
      margin-bottom: 28px;
    }
    .cards {
      display: flex;
      justify-content: center;
      height: 112px;
      margin-bottom: 28px;
    }
    music-card {
      width: 84px;
      flex-shrink: 0;
      border-radius: var(--radius-xs);
      overflow: hidden;
      box-shadow: var(--shadow-panel);
    }
    music-card:first-child {
      transform: rotate(-12deg) translate(14px, 10px);
    }
    music-card:nth-child(2) {
      z-index: 1;
    }
    music-card:last-child {
      transform: rotate(12deg) translate(-14px, 10px);
    }
    h1 {
      margin: 0;
      font-size: var(--font-size-display);
      font-weight: var(--font-weight-medium);
      line-height: 1.2;
    }
    .intro {
      margin: 10px auto 0;
      max-width: 460px;
      color: var(--color-muted);
      font-size: var(--font-size-body);
      text-wrap: balance;
    }
    .starters {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
      margin-top: 16px;
    }
    .starter {
      display: grid;
      grid-template-columns: 16px minmax(0, 1fr);
      gap: 2px 10px;
      padding: 12px;
      border: 1px solid var(--color-border-subtle);
      border-radius: var(--radius-card);
      background: transparent;
      color: var(--color-text);
      text-align: left;
      transition:
        background 0.15s,
        border-color 0.15s;
    }
    .starter:hover:not(:disabled) {
      border-color: var(--color-border);
      background: var(--color-hover);
    }
    .starter svg {
      grid-row: span 2;
      margin-top: 2px;
      color: var(--color-faint);
    }
    .starter strong {
      font-size: var(--font-size-label);
      font-weight: var(--font-weight-medium);
    }
    .starter span {
      color: var(--color-faint);
      font-size: var(--font-size-caption);
    }
    @media (max-width: 640px) {
      .content {
        justify-content: flex-start;
        padding: 24px 16px;
      }
      .starters {
        grid-template-columns: 1fr;
      }
    }
  `;
  render() {
    return html`<div class="content">
      <section class="hero" aria-labelledby="welcome-title">
        <div class="cards" aria-label=${msg("Beispielkarten")}>
          ${exampleCards.map((card, i) => html`<music-card .card=${card} .index=${i}></music-card>`)}
        </div>
        <h1 id="welcome-title">${msg("Jeder Hit hat seine Zeit.")} ${msg("Welche ist deine?")}</h1>
        <p class="intro">${msg("Mach aus deinen Lieblingssongs ein eigenes Kartenspiel.")}</p>
      </section>
      <slot></slot>
      <div class="starters" aria-label=${msg("Ein bisschen Inspiration für den Anfang")}>
        ${starters().map((starter) => html`<button class="starter" ?disabled=${this.pending} @click=${() => this.select(starter.prompt)}>${icon(starter.icon, 16)}<strong>${starter.title}</strong><span>${starter.description}</span></button>`)}
      </div>
    </div>`;
  }
}
