import { css, html, LitElement } from "lit";
import { customElement, property } from "lit/decorators.js";
import "./track-cover";

/**
 * Deck artwork like a Spotify playlist: a 2×2 mosaic once four distinct covers
 * exist, otherwise the first cover (or the neutral placeholder).
 */
@customElement("deck-cover")
export class DeckCover extends LitElement {
  @property({ attribute: false }) urls: readonly string[] = [];
  static styles = css`
    :host {
      display: block;
      aspect-ratio: 1;
      overflow: hidden;
      border-radius: var(--radius-xs);
    }
    .mosaic {
      display: grid;
      grid-template-columns: 1fr 1fr;
      width: 100%;
      height: 100%;
    }
    track-cover {
      border-radius: 0;
    }
    :host > track-cover {
      width: 100%;
      height: 100%;
    }
  `;
  render() {
    return this.urls.length >= 4
      ? html`<div class="mosaic">
          ${this.urls.slice(0, 4).map((url) => html`<track-cover .src=${url}></track-cover>`)}
        </div>`
      : html`<track-cover .src=${this.urls[0]}></track-cover>`;
  }
}
