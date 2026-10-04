import { msg, localized } from "@lit/localize";
import { css, html, LitElement, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import {
  searchSpotify,
  type SpotifyUnifiedSearchResponse,
  type SpotifySearchType,
} from "@api/generated/spotify";
import { pageStyles } from "@shared/styles/page";
import { emit, errorMessage } from "@shared/events";
import { icon } from "@shared/ui/icons";

@customElement("spotify-search")
@localized()
export class SpotifySearch extends LitElement {
  @property({ type: Boolean }) references = false;
  @property({ type: Boolean }) disabled = false;
  @state() private query = "";
  @state() private pending = false;
  @state() private error = "";
  @state() private results?: SpotifyUnifiedSearchResponse;
  private abort?: AbortController;
  private timer?: number;
  disconnectedCallback(): void {
    this.abort?.abort();
    window.clearTimeout(this.timer);
    super.disconnectedCallback();
  }
  private search = async (): Promise<void> => {
    this.abort?.abort();
    const abort = new AbortController();
    this.abort = abort;
    this.error = "";
    if (!this.query.trim()) {
      this.results = undefined;
      this.pending = false;
      return;
    }
    this.pending = true;
    const types: SpotifySearchType[] = this.references ? ["playlist", "artist"] : ["track"];
    try {
      const results = await searchSpotify(
        { query: this.query.trim(), types, limit: 12 },
        { signal: abort.signal },
      );
      if (!abort.signal.aborted) {
        this.results = results;
      }
    } catch (error) {
      if (!abort.signal.aborted) {
        this.error = errorMessage(error);
      }
    } finally {
      if (!abort.signal.aborted) {
        this.pending = false;
      }
    }
  };
  static styles = css`
    ${pageStyles} :host {
      display: block;
    }
    form {
      position: relative;
    }
    input {
      padding-left: 36px !important;
    }
    form svg {
      position: absolute;
      top: 13px;
      left: 12px;
      color: var(--color-muted);
    }
    .results {
      max-height: 290px;
      overflow-y: auto;
      margin-top: 12px;
    }
    .result {
      display: flex;
      align-items: center;
      gap: 10px;
      width: 100%;
      border: 0;
      border-radius: 9px;
      padding: 9px;
      background: transparent;
      color: var(--color-text);
      text-align: left;
    }
    .result:hover {
      background: var(--color-panel);
    }
    .meta {
      flex: 1;
      min-width: 0;
    }
    strong {
      display: block;
      font-size: 12px;
    }
    small {
      display: block;
      color: var(--color-muted);
      font-size: 10px;
    }
    img {
      width: 36px;
      height: 36px;
      object-fit: cover;
      border-radius: 6px;
    }
    .hint {
      font-size: 11px;
      color: var(--color-muted);
    }
  `;
  render() {
    const results = this.results;
    const items = this.references
      ? [
          ...(results?.playlists ?? []).map((item) => ({
            id: item.id,
            title: item.name,
            subtitle: item.owner ?? msg("Playlist"),
            imageUrl: item.coverUrl,
            kind: "spotify-playlist" as const,
          })),
          ...(results?.artists ?? []).map((item) => ({
            id: item.id,
            title: item.name,
            subtitle: msg("Künstler:in"),
            imageUrl: item.imageUrl,
            kind: "spotify-artist" as const,
          })),
        ]
      : [];
    return html`<form
        @submit=${(event: Event) => {
          event.preventDefault();
          window.clearTimeout(this.timer);
          void this.search();
        }}
      >
        ${icon("search", 16)}<input
          class="input"
          type="search"
          aria-label=${this.references ? msg("Playlists und Künstler suchen") : msg("Songs suchen")}
          placeholder=${this.references ? msg("Playlist oder Künstler:in …") : msg("Song oder Interpret:in …")}
          maxlength="200"
          .value=${this.query}
          @input=${(event: Event) => {
            this.query = (event.target as HTMLInputElement).value;
            this.abort?.abort();
            this.results = undefined;
            window.clearTimeout(this.timer);
            this.timer = window.setTimeout(this.search, 300);
          }}
        />
      </form>
      ${this.pending ? html`<p class="hint" role="status">${msg("Spotify wird durchsucht …")}</p>` : nothing}${this.error ? html`<p class="error" role="alert">${this.error}</p>` : nothing}
      <div class="results">
        ${items.map(
          (item) =>
            html`<button
              class="result"
              ?disabled=${this.disabled}
              @click=${() => emit(this, "reference-select", { ...item, spotifyId: item.id })}
            >
              ${item.imageUrl ? html`<img src=${item.imageUrl} alt="" />` : icon("music")}<span
                class="meta"
                ><strong>${item.title}</strong><small>${item.subtitle}</small></span
              >${icon("plus", 16)}
            </button>`,
        )}${
          !this.references
            ? results?.tracks.map(
                (track) =>
                  html`<button
                    class="result"
                    ?disabled=${this.disabled}
                    @click=${() => emit(this, "track-select", track)}
                  >
                    ${track.coverUrl ? html`<img src=${track.coverUrl} alt="" />` : icon("music")}<span
                      class="meta"
                      ><strong>${track.title}</strong
                      ><small>${track.artist} · ${track.year}</small></span
                    >${icon("plus", 16)}
                  </button>`,
              )
            : nothing
        }
      </div>
      ${results && !this.pending && (this.references ? !items.length : !results.tracks.length) ? html`<p class="hint">${msg("Keine Treffer. Probiere einen anderen Suchbegriff.")}</p>` : nothing}`;
  }
}
