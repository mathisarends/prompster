import { css, html, LitElement } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { icon } from "@shared/ui/icons";

/** Spotify album art; falls back to Spotify's neutral placeholder when missing or broken. */
@customElement("track-cover")
export class TrackCover extends LitElement {
  @property() src: string | null | undefined = null;
  @state() private broken = false;
  protected willUpdate(changed: Map<string, unknown>): void {
    if (changed.has("src")) {
      this.broken = false;
    }
  }
  static styles = css`
    :host {
      display: block;
      aspect-ratio: 1;
      overflow: hidden;
      border-radius: var(--radius-xs);
      background: var(--color-control);
    }
    img {
      display: block;
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
    .fallback {
      display: grid;
      place-items: center;
      width: 100%;
      height: 100%;
      color: var(--color-faint);
    }
    .fallback svg {
      width: 40%;
      height: 40%;
    }
  `;
  render() {
    return this.src && !this.broken
      ? html`<img src=${this.src} alt="" loading="lazy" @error=${() => (this.broken = true)} />`
      : html`<span class="fallback">${icon("music", 24)}</span>`;
  }
}
