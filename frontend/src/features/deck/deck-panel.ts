import { css, html, LitElement, nothing, type PropertyValues } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { UserMeResponse } from "@api/generated/users";
import type { UserCurationEventResponse } from "@api/generated/sessions";
import type { SpotifyTrackResponse } from "@api/generated/spotify";
import type { ChatPlaylist } from "@features/chat/state/chat-reducer";
import { pageStyles } from "@shared/styles/page";
import { icon, type IconName } from "@shared/ui/icons";
import { emit } from "@shared/events";
import { DeckController } from "./deck-controller";
import { PlaybackController } from "@features/spotify/playback-controller";
import { OAuthController } from "@features/auth/oauth-controller";
import "@features/spotify/spotify-search";
import "./components/music-card";

const views = [
  { id: "playlist", label: "Playlist", icon: "playlist" },
  { id: "cards", label: "Karten", icon: "cards" },
  { id: "export", label: "Export", icon: "download" },
] as const satisfies readonly { id: string; label: string; icon: IconName }[];

@customElement("deck-panel")
export class DeckPanel extends LitElement {
  @property() sessionId = "";
  @property({ attribute: false }) playlist: ChatPlaylist | null = null;
  @property({ attribute: false }) user!: UserMeResponse;
  @property({ attribute: false }) curationEvents: UserCurationEventResponse[] = [];
  @property({ type: Boolean }) busy = false;
  @property({ type: Boolean }) expanded = false;
  @state() private tab = "playlist";
  @state() private search = false;
  @state() private concealed = false;
  private deck = new DeckController(this);
  private playback = new PlaybackController(this);
  private oauth = new OAuthController(this, async () => {
    emit(this, "user-refresh");
  });
  protected willUpdate(changed: PropertyValues): void {
    if (changed.has("sessionId") || changed.has("playlist")) {
      this.deck.reset();
    }
  }
  private selectTab(event: KeyboardEvent): void {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
      return;
    }
    event.preventDefault();
    const current = views.findIndex((view) => view.id === this.tab);
    const index =
      event.key === "Home"
        ? 0
        : event.key === "End"
          ? views.length - 1
          : (current + (event.key === "ArrowRight" ? 1 : -1) + views.length) % views.length;
    this.tab = views[index].id;
    void this.updateComplete.then(() =>
      this.renderRoot.querySelector<HTMLButtonElement>(`#tab-${this.tab}`)?.focus(),
    );
  }
  static styles = css`
    ${pageStyles}
    :host {
      display: flex;
      flex-direction: column;
      min-height: 0;
      background: var(--color-sidebar);
    }
    header {
      display: flex;
      align-items: center;
      gap: 4px;
      height: 58px;
      flex: 0 0 58px;
      padding: 0 10px;
      border-bottom: 1px solid var(--color-border);
    }
    .tabs {
      display: flex;
      align-items: center;
      flex: 1;
      min-width: 0;
      gap: 3px;
    }
    .tabs button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      min-height: 33px;
      padding: 6px 9px;
      border: 1px solid transparent;
      border-radius: 7px;
      background: transparent;
      color: var(--color-muted);
      font-size: 12px;
    }
    .tabs button[aria-selected="true"] {
      color: var(--color-text);
      border-color: var(--color-border);
      background: var(--color-panel);
    }
    .tabs button:hover {
      color: var(--color-text);
    }
    header .icon-button {
      width: 28px;
      height: 32px;
    }
    .body {
      flex: 1;
      min-height: 0;
      overflow-y: auto;
      padding: 20px;
    }
    .subhead {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      margin-bottom: 18px;
    }
    h2 {
      margin: 0;
      font-size: 17px;
    }
    .subtitle {
      font-size: 11px;
      color: var(--color-muted);
      margin: 6px 0 0;
    }
    .track {
      display: flex;
      align-items: center;
      gap: 11px;
      border-bottom: 1px solid var(--color-border);
      padding: 12px 0;
    }
    .cover {
      border: 0;
      border-radius: 7px;
      background: var(--color-panel);
      color: var(--color-accent);
      padding: 0;
      width: 38px;
      height: 38px;
      flex-shrink: 0;
      display: grid;
      place-items: center;
      position: relative;
    }
    .cover img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      border-radius: inherit;
    }
    .cover:hover::after {
      content: "▶";
      position: absolute;
      inset: 0;
      display: grid;
      place-items: center;
      color: white;
      background: #0008;
    }
    .meta {
      flex: 1;
      min-width: 0;
    }
    .meta strong {
      display: block;
      font-size: 12px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .meta span {
      display: block;
      font-size: 10px;
      color: var(--color-muted);
    }
    .year {
      font: 11px var(--font-mono);
      color: var(--color-muted);
    }
    .track .icon-button {
      width: 26px;
    }
    spotify-search {
      margin-bottom: 20px;
    }
    .cards {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
    }
    music-card {
      max-width: 300px;
    }
    :host(.expanded) .cards {
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    }
    .card-options {
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 10px;
      margin: 22px 0 18px;
    }
    .card-options label {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      margin: 0;
      font-size: 12px;
    }
    .card-options span {
      font-size: 11px;
      color: var(--color-muted);
    }
    @media (max-width: 380px) {
      .tabs button {
        padding-inline: 6px;
        gap: 4px;
      }
      .tabs svg {
        display: none;
      }
      .cards {
        gap: 10px;
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
      .body {
        padding: 16px;
      }
    }
    .export {
      border: 1px solid var(--color-border);
      border-radius: 14px;
      padding: 20px;
      margin-bottom: 16px;
    }
    .export h3 {
      margin: 8px 0;
      font-size: 15px;
    }
    .export p {
      color: var(--color-muted);
      font-size: 12px;
    }
    .export .button {
      margin: 6px 6px 0 0;
    }
    iframe {
      width: 100%;
      height: 440px;
      border: 0;
      margin-top: 16px;
      border-radius: 10px;
    }
    .player {
      padding: 14px 20px;
      border-top: 1px solid var(--color-border);
    }
    .player .line {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 11px;
    }
    .player input {
      width: 100%;
    }
    .connect {
      padding: 10px 0;
      font-size: 11px;
      color: var(--color-muted);
    }
    .undo {
      font-size: 11px;
      margin: 10px 0;
      color: var(--color-muted);
    }
  `;
  render() {
    const tracks = this.playlist?.tracks ?? [];
    const disabled = this.busy || !!this.deck.pending || !this.sessionId;
    const years = tracks.map((track) => track.year);
    const active = tracks.find((track) => track.spotifyUri === this.playback.uri);
    return html`<header aria-label="Deck-Arbeitsbereich">
        <div class="tabs" role="tablist" aria-label="Deckansicht">
          ${views.map(
            ({ id, label, icon: symbol }) =>
              html`<button
                id=${`tab-${id}`}
                role="tab"
                aria-selected=${this.tab === id}
                tabindex=${this.tab === id ? "0" : "-1"}
                aria-controls="deck-content"
                @keydown=${this.selectTab}
                @click=${() => (this.tab = id)}
              >
                ${icon(symbol, 14)}${label}
              </button>`,
          )}
        </div>
        <button
          class="icon-button"
          aria-label=${this.expanded ? "Geteilte Ansicht" : "Deck vergrößern"}
          title=${this.expanded ? "Geteilte Ansicht" : "Deck vergrößern"}
          @click=${() => emit(this, "toggle-expand")}
        >
          ${icon(this.expanded ? "minimize" : "maximize", 15)}
        </button>
        <button
          class="icon-button"
          aria-label="Deck schließen"
          @click=${() => emit(this, "close-panel")}
        >
          ${icon("close", 17)}
        </button>
      </header>
      <section
        id="deck-content"
        class="body"
        role="tabpanel"
        tabindex="0"
        aria-labelledby=${`tab-${this.tab}`}
      >
        ${this.deck.error || this.playback.error || this.oauth.error ? html`<p class="error" role="alert">${this.deck.error || this.playback.error || this.oauth.error}</p>` : nothing}
        <div class="subhead">
          <div>
            <h2>${this.playlist?.name || "Dein Soundtrack"}</h2>
            <p class="subtitle">
              ${tracks.length ? `${Math.min(...years)} – ${Math.max(...years)} · ${tracks.length} Erinnerungen auf Karten` : "Deine Songs erscheinen hier live."}
            </p>
          </div>
          ${this.tab === "playlist" ? html`<button class="icon-button" aria-label="Songs hinzufügen" aria-expanded=${this.search} ?disabled=${disabled} @click=${() => (this.search = !this.search)}>${icon("plus", 19)}</button>` : nothing}
        </div>
        ${
          this.tab === "playlist"
            ? html`${this.search ? html`<spotify-search ?disabled=${disabled} @track-select=${(event: CustomEvent<SpotifyTrackResponse>) => this.deck.add(this.sessionId, event.detail)}></spotify-search>` : nothing}
              ${!this.user.spotifyConnected ? html`<div class="connect">Verbinde Spotify für die Wiedergabe und den Playlist-Export. <button class="text-button" ?disabled=${!!this.oauth.pending} @click=${() => this.oauth.start("spotify-connect")}>Spotify verbinden</button></div>` : !this.user.spotifyPremium ? html`<p class="connect">Wiedergabe im Browser benötigt Spotify Premium. Suche und Export bleiben verfügbar.</p>` : nothing}
              ${tracks.map(
                (track) =>
                  html`<div class="track">
                    <button
                      class="cover"
                      aria-label=${`${track.title} ${active?.id === track.id && !this.playback.paused ? "pausieren" : "abspielen"}`}
                      ?disabled=${!this.user.spotifyPremium || !track.spotifyUri || this.playback.busy}
                      @click=${() => this.playback.toggle(track.spotifyUri!)}
                    >
                      ${track.coverUrl ? html`<img src=${track.coverUrl} alt="" loading="lazy" />` : icon("music", 18)}
                    </button>
                    <div class="meta">
                      <strong>${track.title}</strong><span>${track.artist}</span>
                    </div>
                    <span class="year">${track.year}</span
                    ><button
                      class="icon-button"
                      title="Song entfernen"
                      aria-label=${`${track.title} entfernen`}
                      ?disabled=${disabled}
                      @click=${() => this.deck.remove(this.sessionId, track.id)}
                    >
                      ${icon("close", 14)}
                    </button>
                  </div>`,
              )}
              ${this.curationEvents.filter((event) => event.eventType === "track_removed").map((event) => html`<p class="undo">„${event.trackTitle}“ entfernt. <button class="text-button" ?disabled=${disabled} @click=${() => this.deck.restore(this.sessionId, event.id)}>Rückgängig</button></p>`)}`
            : nothing
        }
        ${
          this.tab === "cards"
            ? html`<div class="card-options">
                  <label
                    ><input
                      type="checkbox"
                      .checked=${this.concealed}
                      @change=${(event: Event) => (this.concealed = (event.target as HTMLInputElement).checked)}
                    />
                    Auflösung verbergen</label
                  >
                  <span>5 × 5 cm · ${this.concealed ? "QR-Seite" : "Auflösung"}</span>
                </div>
                <div class="cards">
                  ${tracks.map((track, i) => html`<music-card .card=${track} .index=${i} ?concealed=${this.concealed}></music-card>`)}
                </div>`
            : nothing
        }
        ${
          this.tab === "export"
            ? html`<div class="export">
                  ${icon("layers", 22)}
                  <h3>Vom Bildschirm an den Spieltisch.</h3>
                  <p>Lade dein Deck als druckfertige PDF mit Musik-QR-Codes herunter.</p>
                  <button
                    class="button primary"
                    ?disabled=${disabled || !tracks.length}
                    @click=${() => this.deck.pdf(this.sessionId, false)}
                  >
                    ${icon("download", 15)}
                    ${this.deck.pending === "pdf" ? "PDF wird erstellt …" : "PDF herunterladen"}</button
                  ><button
                    class="button"
                    ?disabled=${disabled || !tracks.length}
                    @click=${() => this.deck.pdf(this.sessionId, true)}
                  >
                    Vorschau</button
                  >${this.deck.pdfUrl ? html`<iframe title="PDF-Kartenvorschau" src=${this.deck.pdfUrl}></iframe>` : nothing}
                </div>
                <div class="export">
                  ${icon("music", 22)}
                  <h3>Deine Songs auf Spotify</h3>
                  <p>Erstelle eine Playlist in deinem verbundenen Spotify-Konto.</p>
                  <button
                    class="button"
                    ?disabled=${disabled || !tracks.length || !this.user.spotifyConnected}
                    @click=${() => this.deck.spotify(this.sessionId)}
                  >
                    ${this.deck.pending === "spotify" ? `Wird exportiert … ${this.deck.retry}` : "Nach Spotify exportieren"}</button
                  >${this.deck.exported ? html`<p role="status">Playlist erstellt. <a href=${this.deck.exported.url} target="_blank" rel="noopener noreferrer">In Spotify öffnen</a></p>` : nothing}
                </div>`
            : nothing
        }
        ${
          !tracks.length && this.tab !== "export"
            ? html`<div class="status">
                ${icon("disc", 36)}
                <p>Noch ist die Bühne leer.</p>
                <p class="subtitle">
                  Beschreibe dein Wunschdeck im Chat oder füge einen Song über die Suche hinzu.
                </p>
              </div>`
            : nothing
        }
      </section>
      ${
        active
          ? html`<footer class="player">
              <div class="line">
                <button
                  class="icon-button"
                  aria-label=${this.playback.paused ? "Wiedergabe fortsetzen" : "Wiedergabe pausieren"}
                  @click=${() => this.playback.toggle(active.spotifyUri!)}
                >
                  ${this.playback.paused ? "▶" : "Ⅱ"}</button
                ><span>${active.title} · ${active.artist}</span>
              </div>
              <input
                type="range"
                aria-label="Wiedergabeposition"
                min="0"
                max=${this.playback.duration || 1}
                .value=${String(this.playback.position)}
                @change=${(event: Event) => this.playback.seek(Number((event.target as HTMLInputElement).value))}
              /><label class="line"
                >Lautstärke<input
                  type="range"
                  aria-label="Lautstärke"
                  min="0"
                  max="1"
                  step="0.01"
                  .value=${String(this.playback.volume)}
                  @change=${(event: Event) => this.playback.setVolume(Number((event.target as HTMLInputElement).value))}
              /></label>
            </footer>`
          : nothing
      }`;
  }
}
