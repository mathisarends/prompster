import { css, html, LitElement, svg, type PropertyValues } from "lit";
import { customElement, property } from "lit/decorators.js";
import { styleMap } from "lit/directives/style-map.js";
import QRCode from "qrcode";

export type SongCard = {
  id: string;
  title: string;
  artist: string;
  year: number;
  spotifyUri?: string | null;
};

// Same palette, order and angles as the printable deck's deck.typ.
const gradients = [
  ["#e91e63", "#f06292"],
  ["#00bcd4", "#4dd0e1"],
  ["#4caf50", "#81c784"],
  ["#ff9800", "#ffb74d"],
  ["#9c27b0", "#ce93d8"],
  ["#ffeb3b", "#fff176"],
  ["#2196f3", "#64b5f6"],
  ["#ef5350", "#ff8a80"],
  ["#26a69a", "#80cbc4"],
  ["#ab47bc", "#e040fb"],
];
const angles = [135, 45, 160, 20, 110, 70, 150, 30, 140, 50];

@customElement("music-card")
export class MusicCard extends LitElement {
  @property({ attribute: false }) card?: SongCard;
  @property({ type: Number }) index = 0;
  @property({ type: Boolean }) concealed = false;
  private qr?: { path: string; size: number };

  protected willUpdate(changed: PropertyValues): void {
    if (!changed.has("card")) {
      return;
    }
    this.qr = undefined;
    const match = this.card?.spotifyUri?.match(/^spotify:track:([a-zA-Z0-9-]+)$/);
    if (match) {
      const { modules } = QRCode.create(`https://open.spotify.com/track/${match[1]}`, {
        errorCorrectionLevel: "M",
      });
      const path = Array.from(modules.data, (dark, i) =>
        dark ? `M${(i % modules.size) + 4} ${Math.floor(i / modules.size) + 4}h1v1h-1z` : "",
      ).join("");
      this.qr = { path, size: modules.size + 8 };
    }
  }

  static styles = css`
    :host {
      display: block;
      container-type: inline-size;
    }
    * {
      box-sizing: border-box;
    }
    article {
      position: relative;
      width: 100%;
      aspect-ratio: 1;
      overflow: hidden;
      color: #000;
      font-family: "New Computer Modern", "Latin Modern Roman", "Times New Roman", serif;
      box-shadow: 0 5px 16px #0002;
    }
    .answer::before {
      content: "";
      position: absolute;
      inset: 2.12%;
      border: 0.7cqw solid #0005;
      border-radius: 0.7cqw;
    }
    .details {
      position: absolute;
      inset: 0 8%;
      display: grid;
      grid-template-rows: 25cqw 0.7cqw 32cqw 0.7cqw 25cqw;
      align-content: center;
      text-align: center;
    }
    .artist,
    .title {
      display: grid;
      align-content: center;
      margin: 0;
      font-size: 6cqw;
      line-height: 1.15;
      overflow-wrap: anywhere;
    }
    .artist {
      font-weight: bold;
    }
    .title {
      font-style: italic;
    }
    .year {
      display: grid;
      place-items: center;
      font-size: 28cqw;
      font-weight: 900;
      line-height: 1;
    }
    .rule {
      width: 50%;
      height: 100%;
      margin: auto;
      background: #0008;
    }
    .front {
      background: #0d0d0d;
      display: grid;
      place-items: center;
    }
    .record {
      position: absolute;
      inset: 2%;
      width: 96%;
      height: 96%;
    }
    .qr {
      position: relative;
      width: 50%;
      height: 50%;
      background: white;
    }
    .missing {
      max-width: 65%;
      text-align: center;
      font: 6cqw var(--font-sans);
      color: #f4c6fa;
    }
    .dot {
      position: absolute;
      width: 2.12%;
      height: 2.12%;
      background: #e040fb99;
      border-radius: 50%;
    }
    .tl {
      top: 2.8%;
      left: 2.8%;
    }
    .tr {
      top: 2.8%;
      right: 2.8%;
    }
    .bl {
      bottom: 2.8%;
      left: 2.8%;
    }
    .br {
      bottom: 2.8%;
      right: 2.8%;
    }
  `;

  render() {
    if (!this.card) {
      return html``;
    }
    const index = Math.abs(Math.trunc(this.index));
    const [start, end] = gradients[(index * 7 + 3) % gradients.length];
    const angle = 90 + angles[(index * 3 + 1) % angles.length];
    return this.concealed
      ? html`<article class="front" aria-label="Verdeckte Musik-Karte">
          <svg class="record" viewBox="0 0 100 100" aria-hidden="true">
            ${Array.from({ length: 12 }, (_, i) => svg`<circle cx="50" cy="50" r=${((i + 1) * 50) / 12} fill="none" stroke="#e040fb" stroke-opacity=${(i + 1) % 2 === 0 ? 0.15 : 0.08} stroke-width="0.85" />`)}
            <circle cx="50" cy="50" r="49.8" fill="none" stroke="#c724b180" stroke-width="0.42" />
          </svg>
          ${this.qr ? svg`<svg class="qr" viewBox=${`0 0 ${this.qr.size} ${this.qr.size}`} role="img" aria-label="Spotify-QR-Code" shape-rendering="crispEdges"><path d=${this.qr.path} fill="black" /></svg>` : html`<span class="missing">Kein Spotify-Link</span>`}
          <i class="dot tl"></i><i class="dot tr"></i><i class="dot bl"></i><i class="dot br"></i>
        </article>`
      : html`<article
          class="answer"
          style=${styleMap({ background: `linear-gradient(${angle}deg, ${start}, ${end})` })}
          aria-label=${`${this.card.title}, ${this.card.artist}, ${this.card.year}`}
        >
          <div class="details">
            <p class="artist">${this.card.artist}</p>
            <div class="rule"></div>
            <strong class="year">${this.card.year}</strong>
            <div class="rule"></div>
            <p class="title">${this.card.title}</p>
          </div>
        </article>`;
  }
}
