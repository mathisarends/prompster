import { msg, localized } from "@lit/localize";
import { css, html, LitElement, nothing, svg, type PropertyValues } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { styleMap } from "lit/directives/style-map.js";
import QRCode from "qrcode";
import {
  eraLabels,
  eraOf,
  paletteForYear,
  paletteFromImage,
  type CoverPalette,
  type Era,
} from "./card-design";

export type SongCard = {
  id: string;
  title: string;
  artist: string;
  year: number;
  spotifyUri?: string | null;
  coverUrl?: string | null;
};

/** Palettes of covers already seen, so cards keep their colour across renders. */
const palettes = new Map<string, CoverPalette>();

const equaliserLevels = [0.45, 0.8, 0.6, 1, 0.7, 0.35, 0.9, 0.55];

const reel = (x: number, y: number) =>
  svg`<g transform="translate(${x} ${y})">
    <circle r="3.63" fill="#f3efe6" />
    <circle r="2.18" fill="#1b1b1d" />
    ${[0, 60, 120].map((angle) => svg`<rect x="-0.36" y="-2.03" width="0.72" height="4.06" fill="#f3efe6" transform="rotate(${angle})" />`)}
    <circle r="0.87" fill="#1b1b1d" />
  </g>`;

const record = (x: number, y: number, radius: number) =>
  svg`<g transform="translate(${x} ${y})">
    <circle r=${radius} fill="#141414" />
    ${Array.from({ length: 8 }, (_, i) => svg`<circle r=${(radius * (i + 4)) / 12.5} fill="none" stroke="#fff" stroke-opacity=${i % 2 ? 0.18 : 0.1} stroke-width="0.25" />`)}
    <circle r=${radius * 0.34} class="label" />
    <circle r=${radius * 0.34 - 1.2} fill="none" stroke="#000" stroke-opacity="0.4" stroke-width="0.25" />
    <circle r=${radius * 0.044} fill="#141414" />
  </g>`;

/** The medium behind the cover, drawn on the card's 100-unit grid like deck.typ. */
const scenes: Record<Era, (year: number) => unknown> = {
  lp: () =>
    svg`${record(69, 30.5, 22)}<rect class="shadow" x="13.2" y="8.2" width="47" height="47" />`,
  mc: () => svg`
    <clipPath id="tape"><rect x="40" y="14" width="50" height="33" rx="2.2" /></clipPath>
    <g clip-path="url(#tape)">
      <rect x="40" y="14" width="50" height="33" fill="#26262a" />
      <rect x="43" y="17" width="44" height="20.46" rx="1.4" fill="#f3ead7" />
      <rect class="accent" x="43" y="29.96" width="44" height="2.2" />
      <rect class="accent" x="43" y="32.86" width="44" height="1" />
      <rect x="50" y="22.25" width="30" height="8.91" rx="1.6" fill="#101012" />
      ${reel(56.63, 26.7)}${reel(73.37, 26.7)}
      <polygon points="49,47 53.5,39.08 76.5,39.08 81,47" fill="#19191c" />
      <circle cx="59" cy="43.4" r="1.3" fill="#f3ead7" fill-opacity="0.7" />
      <circle cx="71" cy="43.4" r="1.3" fill="#f3ead7" fill-opacity="0.7" />
    </g>
    <rect class="shadow" x="13.2" y="8.2" width="47" height="47" rx="1.5" />`,
  cd: () => svg`
    <rect class="shadow" x="13.2" y="8.2" width="52" height="47" rx="0.8" />
    <rect x="12" y="7" width="52" height="47" rx="0.8" fill="#dfe1e6" />
    ${Array.from({ length: 6 }, (_, i) => svg`<rect x="13.4" y=${9.5 + i * 8} width="2.2" height="3" rx="0.4" fill="#a9acb6" />`)}`,
  stream: (year) => svg`
    ${equaliserLevels.map((level, bar) => {
      const wobble = Math.abs(Math.sin(((bar * 37 + year * 13) * Math.PI) / 180));
      const height = 26 * (wobble * 0.6 + level * 0.4);
      return svg`<rect class=${bar === 3 ? "accent" : "ink"} x=${65 + bar * 3.4} y=${38 - height} width="2.1" height=${height} rx="1" />`;
    })}
    <rect class="ink" x="65" y="43" width="26.5" height="0.8" rx="0.4" fill-opacity="0.25" />
    <rect class="ink" x="65" y="43" width="11" height="0.8" rx="0.4" />
    <circle class="ink" cx="76.5" cy="43.4" r="1.3" />
    <rect class="shadow" x="13.2" y="8.2" width="47" height="47" rx="5" />`,
};

/**
 * One deck card in the "Zeitkapsel" design. The answer side shows the cover in
 * the medium of its era; the concealed side is the same card before the reveal,
 * with the Spotify code where the cover will be.
 */
@customElement("music-card")
@localized()
export class MusicCard extends LitElement {
  @property({ attribute: false }) card?: SongCard;
  @property({ type: Boolean }) concealed = false;
  @state() private palette: CoverPalette = paletteForYear(0);
  /** Covers load with CORS so their pixels can be read; a refusal retries without. */
  @state() private readable = true;
  @state() private broken = false;
  private qr?: { path: string; size: number };

  protected willUpdate(changed: PropertyValues): void {
    if (!changed.has("card") || !this.card) {
      return;
    }
    const { coverUrl, spotifyUri, year } = this.card;
    this.readable = true;
    this.broken = false;
    this.palette = (coverUrl && palettes.get(coverUrl)) || paletteForYear(year);
    this.qr = undefined;
    const match = spotifyUri?.match(/^spotify:track:([a-zA-Z0-9-]+)$/);
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

  protected firstUpdated(): void {
    void document.fonts.ready.then(() => this.fitText());
  }

  protected updated(): void {
    this.fitText();
  }

  /** Shrinks artist and title until they fit on one line, like `fit` in deck.typ. */
  private fitText(): void {
    for (const line of this.renderRoot.querySelectorAll<HTMLElement>(".fit")) {
      line.style.fontSize = "";
      if (line.scrollWidth > line.clientWidth) {
        const size = (6.2 * line.clientWidth) / line.scrollWidth;
        line.style.fontSize = `${Math.max(4, size)}cqw`;
      }
    }
  }

  private coverLoaded(event: Event): void {
    const url = this.card?.coverUrl;
    const palette = this.readable ? paletteFromImage(event.target as HTMLImageElement) : null;
    if (url && palette) {
      palettes.set(url, palette);
      this.palette = palette;
    }
  }

  private coverFailed(): void {
    if (this.readable) {
      this.readable = false;
    } else {
      this.broken = true;
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
      box-shadow: 0 5px 16px #0002;
      /* Keep in sync with palette_of in deck.typ. */
      --paper: hsl(var(--hue) calc(var(--sat) * 90%) 90%);
      --ink: hsl(var(--hue) calc(var(--sat) * 70%) 13%);
      --mid: hsl(var(--hue) calc(var(--sat) * 80%) 40%);
      --accent: hsl(var(--hue) calc(min(1, var(--sat) * 1.15) * 100%) 60%);
      color: var(--ink);
      background: var(--paper);
      transition: background 0.3s;
    }
    .concealed {
      --paper: #f4ecdc;
      --ink: #1b1820;
      --accent: #ff5a3c;
    }
    article > * {
      position: absolute;
    }
    .sun {
      top: -30cqw;
      left: -20cqw;
      width: 124cqw;
      height: 124cqw;
      border-radius: 50%;
      background: #ffffff73;
    }
    .concealed .sun {
      background: #ffffff8c;
    }
    .scene {
      inset: 0;
      width: 100%;
      height: 100%;
    }
    .scene .label,
    .scene .accent {
      fill: var(--accent);
    }
    .scene .ink {
      fill: var(--ink);
    }
    .scene .shadow {
      fill: var(--ink);
      fill-opacity: 0.22;
    }
    .scene text {
      fill: var(--paper);
      font:
        8px "Archivo Black",
        sans-serif;
      text-anchor: middle;
    }
    .disc {
      top: 8.5cqw;
      left: 46cqw;
      width: 44cqw;
      height: 44cqw;
      border: 0.3cqw solid #9a9da8;
      border-radius: 50%;
      background:
        radial-gradient(circle closest-side, #3a3a40 0 15%, #0000 15.5%),
        radial-gradient(circle closest-side, #0000 0 21.4%, #9a9da8 21.7% 22.5%, #0000 22.8%),
        radial-gradient(circle closest-side, #0000 0 39.4%, #9a9da8 39.7% 40.5%, #0000 40.8%),
        radial-gradient(circle closest-side, #e9eaeea6 0 40%, #0000 40.5%),
        conic-gradient(
          from 110deg,
          #f4f4f6,
          #c9ccd4,
          #ffd9f0,
          #d5f3ff,
          #f4f4f6,
          #b9bcc6,
          #fff4c9,
          #d9ffe6,
          #f4f4f6
        );
    }
    /* Cover, and on the concealed side the Spotify code in its place. */
    .cover {
      top: 7cqw;
      left: 12cqw;
      width: 47cqw;
      height: 47cqw;
      overflow: hidden;
      background:
        repeating-radial-gradient(circle at 100% 100%, #0000 0 9.84cqw, #ffffff4d 9.84cqw 10.34cqw),
        linear-gradient(45deg, var(--accent), var(--mid));
    }
    .cover::after {
      content: "";
      position: absolute;
      inset: 0;
      border: 0.3cqw solid color-mix(in srgb, var(--ink) 50%, transparent);
      border-radius: inherit;
    }
    .cover img {
      display: block;
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
    .mc .cover {
      border-radius: 1.5cqw;
    }
    .mc .cover::before {
      content: "";
      position: absolute;
      inset: 0 auto 0 0;
      width: 4.2cqw;
      background: #ffffff8c;
    }
    .cd .cover {
      left: 17cqw;
      border-radius: 0 0.8cqw 0.8cqw 0;
    }
    .cd .cover::after {
      left: -5cqw;
      border-radius: 0.8cqw;
    }
    .stream .cover {
      border-radius: 5cqw;
    }
    .stream .cover::after {
      border: 0;
    }
    .concealed .cover {
      left: 10cqw;
      width: 56cqw;
      height: 56cqw;
      display: grid;
      place-items: center;
      background: #fff;
    }
    .qr {
      width: 100%;
      height: 100%;
    }
    .missing {
      max-width: 80%;
      text-align: center;
      font: 5cqw var(--font-sans);
    }
    .artist,
    .title {
      left: 12cqw;
      width: 76cqw;
      margin: 0;
      overflow: hidden;
      font-family: "Barlow Condensed", var(--font-sans);
      font-size: 6.2cqw;
      line-height: 1;
      white-space: nowrap;
    }
    .artist {
      top: 58.3cqw;
      font-weight: 700;
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }
    .title {
      top: 65.1cqw;
      color: var(--mid);
      font-style: italic;
      font-weight: 500;
    }
    .year {
      bottom: 3.85cqw;
      left: 11.2cqw;
      font:
        22cqw/1 "Archivo Black",
        var(--font-sans);
      letter-spacing: -0.02em;
    }
    .tag {
      right: 8cqw;
      bottom: 7.5cqw;
      padding: 1.6cqw 1.1cqw;
      border: 0.3cqw solid var(--ink);
      border-radius: 0.8cqw;
      font:
        700 2.5cqw/1 "Space Mono",
        var(--font-mono);
      white-space: nowrap;
      writing-mode: vertical-rl;
      transform: rotate(180deg);
    }
    /* Concealed side: artist, title and year are still blanks. */
    .blank {
      left: 10cqw;
      height: 3.2cqw;
      border-radius: 1.6cqw;
      background: var(--ink);
      opacity: 0.22;
    }
    .blank.artist-line {
      top: 67.4cqw;
      width: 40cqw;
    }
    .blank.title-line {
      top: 72.6cqw;
      width: 27cqw;
      opacity: 0.12;
    }
    .concealed .year {
      bottom: 4.2cqw;
      left: 9.4cqw;
      font-size: 17cqw;
      letter-spacing: 0.03em;
      opacity: 0.2;
    }
    .concealed .tag {
      bottom: 7cqw;
      color: var(--paper);
      background: var(--ink);
    }
  `;

  render() {
    if (!this.card) {
      return html``;
    }
    return this.concealed ? this.concealedSide() : this.answerSide(this.card);
  }

  private answerSide(card: SongCard) {
    const era = eraOf(card.year);
    const colours = { "--hue": String(this.palette.hue), "--sat": String(this.palette.saturation) };
    return html`<article
      class=${era}
      style=${styleMap(colours)}
      aria-label=${`${card.title}, ${card.artist}, ${card.year}`}
    >
      <i class="sun"></i>
      ${era === "cd" ? html`<i class="disc"></i>` : nothing}
      <svg class="scene" viewBox="0 0 100 100" aria-hidden="true">${scenes[era](card.year)}</svg>
      <div class="cover">
        ${
          card.coverUrl && !this.broken
            ? html`<img
                src=${card.coverUrl}
                alt=""
                crossorigin=${this.readable ? "anonymous" : nothing}
                @load=${this.coverLoaded}
                @error=${this.coverFailed}
              />`
            : nothing
        }
      </div>
      <p class="artist fit">${card.artist}</p>
      <p class="title fit">${card.title}</p>
      <strong class="year">${card.year}</strong>
      <span class="tag">${eraLabels[era]}</span>
    </article>`;
  }

  private concealedSide() {
    return html`<article class="concealed" aria-label=${msg("Verdeckte Musik-Karte")}>
      <i class="sun"></i>
      <svg class="scene" viewBox="0 0 100 100" aria-hidden="true">
        ${record(73, 34, 23)}
        <text x="73" y="37.05">?</text>
        <rect class="shadow" x="11.2" y="8.2" width="56" height="56" />
      </svg>
      <div class="cover">
        ${
          this.qr
            ? svg`<svg class="qr" viewBox=${`0 0 ${this.qr.size} ${this.qr.size}`} role="img" aria-label=${msg("Spotify-QR-Code")} shape-rendering="crispEdges"><path d=${this.qr.path} fill="black" /></svg>`
            : html`<span class="missing">${msg("Kein Spotify-Link")}</span>`
        }
      </div>
      <i class="blank artist-line"></i>
      <i class="blank title-line"></i>
      <span class="year" aria-hidden="true">????</span>
      <span class="tag" aria-hidden="true">SCAN · LISTEN · GUESS</span>
    </article>`;
  }
}
