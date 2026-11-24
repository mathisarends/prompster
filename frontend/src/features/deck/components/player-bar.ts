import { msg, localized } from "@lit/localize";
import { css, html, LitElement, nothing } from "lit";
import { customElement, property } from "lit/decorators.js";
import { styleMap } from "lit/directives/style-map.js";
import { workspaceStyles } from "@shared/styles/workspace";
import { icon } from "@shared/ui/icons";
import { emit } from "@shared/events";
import "@shared/ui/track-cover";

export type PlayerTrack = {
  title: string;
  artist: string;
  coverUrl?: string | null;
};

const clock = (ms: number) => {
  const seconds = Math.max(0, Math.floor(ms / 1000));
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
};

const setProgress = (event: Event, max: number) => {
  const input = event.target as HTMLInputElement;
  input.style.setProperty("--progress", `${(Number(input.value) / (max || 1)) * 100}%`);
};

/**
 * Spotify-style "now playing" bar. Wide containers get Spotify's desktop
 * three-column layout, narrow ones its compact mobile mini player.
 * Purely presentational: it reports intents as `player-*` events.
 */
@customElement("player-bar")
@localized()
export class PlayerBar extends LitElement {
  @property({ attribute: false }) track: PlayerTrack | null = null;
  @property({ type: Boolean }) playing = false;
  @property({ type: Boolean }) live = false;
  @property({ type: Boolean }) disabled = false;
  @property({ type: Boolean }) busy = false;
  @property({ type: Boolean }) hasPrevious = false;
  @property({ type: Boolean }) hasNext = false;
  @property({ type: Number }) position = 0;
  @property({ type: Number }) duration = 0;
  @property({ type: Number }) volume = 0.72;
  @property() note = "";
  static styles = css`
    ${workspaceStyles}
    :host {
      display: block;
      container-type: inline-size;
      background: var(--color-background);
    }
    .bar {
      display: grid;
      grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.25fr) minmax(0, 0.6fr);
      align-items: center;
      gap: 12px;
      height: 72px;
      padding: 0 16px 0 10px;
    }
    .now {
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 0;
    }
    track-cover {
      width: 48px;
      flex-shrink: 0;
    }
    .meta {
      min-width: 0;
      line-height: 1.3;
    }
    .meta strong,
    .meta span {
      display: block;
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
    }
    .meta strong {
      color: var(--color-text-strong);
      font-size: var(--font-size-body);
      font-weight: var(--font-weight-regular);
    }
    .meta span {
      color: var(--color-muted);
      font-size: var(--font-size-caption);
    }
    .center {
      display: grid;
      justify-items: center;
      gap: 6px;
      min-width: 0;
    }
    .transport {
      display: flex;
      align-items: center;
      gap: 14px;
    }
    .skip {
      display: grid;
      place-items: center;
      width: 32px;
      height: 32px;
      padding: 0;
      border: 0;
      background: none;
      color: var(--color-muted);
    }
    .skip:hover:not(:disabled) {
      color: var(--color-text-strong);
    }
    .skip:disabled,
    .play:disabled {
      opacity: 0.3;
      cursor: default;
    }
    .play {
      display: grid;
      place-items: center;
      width: 32px;
      height: 32px;
      padding: 0;
      border: 0;
      border-radius: 50%;
      background: var(--color-text-strong);
      color: var(--color-inverse);
      transition: transform 0.1s;
    }
    .play:hover:not(:disabled) {
      transform: scale(1.06);
    }
    .progress {
      display: flex;
      align-items: center;
      gap: 8px;
      width: 100%;
      color: var(--color-muted);
      font-size: var(--font-size-micro);
      font-variant-numeric: tabular-nums;
    }
    .time {
      min-width: 30px;
      text-align: right;
    }
    .time.end {
      text-align: left;
    }
    .note {
      margin: 0;
      color: var(--color-muted);
      font-size: var(--font-size-micro);
      text-align: center;
    }
    .volume {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 6px;
      color: var(--color-muted);
    }
    .volume input {
      flex: 0 1 92px;
    }
    /* Spotify's thin range: white fill that turns green with a thumb on hover. */
    input[type="range"] {
      --fill: var(--color-text-strong);
      flex: 1;
      min-width: 0;
      height: 12px;
      margin: 0;
      background: transparent;
      appearance: none;
      cursor: pointer;
    }
    input[type="range"]:hover:not(:disabled),
    input[type="range"]:focus-visible {
      --fill: var(--color-play);
    }
    input[type="range"]:disabled {
      cursor: default;
    }
    input[type="range"]::-webkit-slider-runnable-track {
      height: 4px;
      border-radius: 2px;
      background: linear-gradient(
        to right,
        var(--fill) var(--progress),
        var(--color-player-track) var(--progress)
      );
    }
    input[type="range"]::-webkit-slider-thumb {
      width: 12px;
      height: 12px;
      margin-top: -4px;
      border: 0;
      border-radius: 50%;
      background: var(--color-text-strong);
      box-shadow: 0 2px 4px var(--color-backdrop);
      appearance: none;
      opacity: 0;
    }
    input[type="range"]:hover:not(:disabled)::-webkit-slider-thumb,
    input[type="range"]:focus-visible::-webkit-slider-thumb {
      opacity: 1;
    }
    input[type="range"]::-moz-range-track {
      height: 4px;
      border-radius: 2px;
      background: var(--color-player-track);
    }
    input[type="range"]::-moz-range-progress {
      height: 4px;
      border-radius: 2px;
      background: var(--fill);
    }
    input[type="range"]::-moz-range-thumb {
      width: 12px;
      height: 12px;
      border: 0;
      border-radius: 50%;
      background: var(--color-text-strong);
    }
    input[type="range"]:focus-visible {
      outline: none;
      box-shadow: none;
    }
    /* Compact mini player, like Spotify mobile: card, play icon, hairline progress. */
    .mini {
      display: none;
    }
    @container (max-width: 460px) {
      .bar {
        position: relative;
        margin: 8px;
        grid-template-columns: minmax(0, 1fr) auto;
        height: 56px;
        padding: 0 8px;
        overflow: hidden;
        border-radius: var(--radius-sm);
        background: var(--color-control);
      }
      track-cover {
        width: 40px;
      }
      .meta strong {
        font-weight: var(--font-weight-medium);
      }
      .progress,
      .volume,
      .note,
      .skip {
        display: none;
      }
      .play {
        width: 36px;
        height: 36px;
        background: none;
        color: var(--color-text-strong);
      }
      .mini {
        display: block;
        position: absolute;
        right: 8px;
        bottom: 0;
        left: 8px;
        height: 2px;
        border-radius: 1px;
        background: var(--color-player-track);
      }
      .mini i {
        display: block;
        height: 100%;
        border-radius: inherit;
        background: var(--color-text-strong);
      }
    }
  `;
  render() {
    const track = this.track;
    if (!track) {
      return nothing;
    }
    const position = this.live ? this.position : 0;
    const percent =
      this.live && this.duration ? Math.min(100, (position / this.duration) * 100) : 0;
    return html`<div class="bar">
      <div class="now">
        <track-cover .src=${track.coverUrl}></track-cover>
        <div class="meta">
          <strong title=${track.title}>${track.title}</strong><span>${track.artist}</span>
        </div>
      </div>
      <div class="center">
        <div class="transport">
          <button
            class="skip previous"
            aria-label=${msg("Vorheriger Song")}
            title=${msg("Vorheriger Song")}
            ?disabled=${this.disabled || this.busy || !this.hasPrevious}
            @click=${() => emit(this, "player-previous")}
          >
            ${icon("previous", 16, true)}</button
          ><button
            class="play"
            aria-label=${this.playing ? msg("Wiedergabe pausieren") : msg("Wiedergabe starten")}
            title=${this.playing ? msg("Pausieren") : msg("Abspielen")}
            ?disabled=${this.disabled || this.busy}
            @click=${() => emit(this, "player-toggle")}
          >
            ${this.playing ? icon("pause", 16, true) : icon("play", 16, true)}</button
          ><button
            class="skip"
            aria-label=${msg("Nächster Song")}
            title=${msg("Nächster Song")}
            ?disabled=${this.disabled || this.busy || !this.hasNext}
            @click=${() => emit(this, "player-next")}
          >
            ${icon("next", 16, true)}
          </button>
        </div>
        ${
          this.note
            ? html`<p class="note">${this.note}</p>`
            : html`<div class="progress">
                <span class="time">${clock(position)}</span
                ><input
                  type="range"
                  aria-label=${msg("Wiedergabeposition")}
                  min="0"
                  max=${this.duration || 1}
                  .value=${String(position)}
                  style=${styleMap({ "--progress": `${percent}%` })}
                  ?disabled=${!this.live}
                  @input=${(event: Event) => setProgress(event, this.duration)}
                  @change=${(event: Event) => emit(this, "player-seek", Number((event.target as HTMLInputElement).value))}
                /><span class="time end">${this.live ? clock(this.duration) : "0:00"}</span>
              </div>`
        }
      </div>
      <label class="volume" title=${msg("Lautstärke")}
        >${icon(this.volume ? "volume" : "mute", 16)}<input
          type="range"
          aria-label=${msg("Lautstärke")}
          min="0"
          max="1"
          step="0.01"
          .value=${String(this.volume)}
          style=${styleMap({ "--progress": `${this.volume * 100}%` })}
          ?disabled=${this.disabled}
          @input=${(event: Event) => setProgress(event, 1)}
          @change=${(event: Event) => emit(this, "player-volume", Number((event.target as HTMLInputElement).value))}
      /></label>
      <span class="mini" aria-hidden="true"
        ><i style=${styleMap({ width: `${percent}%` })}></i
      ></span>
    </div>`;
  }
}
