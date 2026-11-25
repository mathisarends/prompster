import { msg, localized, str } from "@lit/localize";
import { retryLabel } from "@shared/i18n/messages";
import { shortcutKeys, shortcutTitle } from "@shared/shortcuts";
import { css, html, LitElement, nothing, type PropertyValues } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { repeat } from "lit/directives/repeat.js";
import type { UserMeResponse } from "@api/generated/users";
import type { UserCurationEventResponse } from "@api/generated/sessions";
import type { SpotifyTrackResponse } from "@api/generated/spotify";
import type { SessionStreamEvent } from "@/api/session-streams";
import type { ChatPlaylist } from "@features/chat/state/chat-reducer";
import type { Feed } from "@shared/feed";
import { pageStyles } from "@shared/styles/page";
import { icon } from "@shared/ui/icons";
import { emit } from "@shared/events";
import { DeckController } from "./deck-controller";
import { Flip } from "./choreography/flip";
import { PlaylistChoreography } from "./choreography/playlist-choreography";
import type { StageSearch } from "./choreography/stage";
import "./choreography/agent-search";
import { PlaybackController } from "@features/spotify/playback-controller";
import { OAuthController } from "@features/auth/oauth-controller";
import "@features/spotify/spotify-search";
import "./components/music-card";
import "@shared/ui/track-cover";
import "./components/player-bar";

const views = [
  { id: "playlist", label: () => msg("Playlist") },
  { id: "cards", label: () => msg("Karten") },
  { id: "export", label: () => msg("Export") },
] as const satisfies readonly { id: string; label: () => string }[];

@customElement("deck-panel")
@localized()
export class DeckPanel extends LitElement {
  @property() sessionId = "";
  @property({ attribute: false }) playlist: ChatPlaylist | null = null;
  @property({ attribute: false }) user!: UserMeResponse;
  @property({ attribute: false }) curationEvents: UserCurationEventResponse[] = [];
  @property({ type: Boolean }) busy = false;
  @property({ type: Boolean }) expanded = false;
  /** The running turn's events; the agent's work on the deck is staged from them. */
  @property({ attribute: false }) stream?: Feed<SessionStreamEvent>;
  @state() private tab = "playlist";
  @state() private search = false;
  @state() private concealed = false;
  private deck = new DeckController(this);
  private choreography = new PlaylistChoreography(this, {
    tracks: () => this.playlist?.tracks ?? [],
    progress: (progress) => emit(this, "stage-progress", progress),
  });
  private flip = new Flip();
  /** The last search the agent showed, kept while its field closes. */
  private agentSearch: StageSearch | null = null;
  private focused: string | null = null;
  private playback = new PlaybackController(this);
  private oauth = new OAuthController(this, async () => {
    emit(this, "user-refresh");
  });
  protected willUpdate(changed: PropertyValues): void {
    if (changed.has("sessionId") || changed.has("playlist")) {
      this.deck.reset();
    }
    if (changed.has("sessionId")) {
      this.choreography.reset();
    }
    if (changed.has("stream")) {
      this.choreography.follow(this.stream);
    }
    if (changed.has("busy")) {
      this.choreography.setRunning(this.busy);
    }
    this.agentSearch = this.choreography.stage?.search ?? this.agentSearch;
    if (this.choreography.stage) {
      this.flip.capture(this.rows);
    }
  }
  protected updated(): void {
    this.flip.play(this.rows);
    const focus = this.choreography.stage?.focus ?? null;
    if (focus && focus !== this.focused) {
      this.renderRoot
        .querySelector(`.track[data-key="${CSS.escape(focus)}"]`)
        ?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
    this.focused = focus;
  }
  private get rows(): NodeListOf<HTMLElement> {
    return this.renderRoot.querySelectorAll<HTMLElement>(".track");
  }
  /** The deck on screen: what the agent's choreography presents, else the deck itself. */
  private get tracks() {
    return this.choreography.stage?.tracks ?? this.playlist?.tracks ?? [];
  }
  private get disabled(): boolean {
    return this.busy || !!this.deck.pending || !this.sessionId || !!this.choreography.stage;
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
  private get playable() {
    return this.tracks.filter((track) => track.spotifyUri);
  }
  /** Track shown in the player: the live Spotify track, else the first playable song. */
  private get current() {
    return (
      this.tracks.find((track) => track.spotifyUri && track.spotifyUri === this.playback.uri) ??
      this.playable[0]
    );
  }
  private step(offset: number): string | undefined {
    const playable = this.playable;
    const index = playable.findIndex((track) => track.id === this.current?.id);
    return playable[index + offset]?.spotifyUri ?? undefined;
  }
  private play(uri: string | null | undefined): void {
    if (uri) {
      void this.playback.toggle(uri);
    }
  }
  private playerNote(): string {
    if (!this.user.spotifyConnected) {
      return msg("Verbinde Spotify, um hier reinzuhören.");
    }
    if (!this.user.spotifyPremium) {
      return msg("Wiedergabe im Browser benötigt Spotify Premium.");
    }
    return "";
  }
  static styles = css`
    ${pageStyles}
    /* Spotify-style workspace: black panel, pill tabs, track table, player below. */
    :host {
      display: flex;
      flex-direction: column;
      min-height: 0;
      border-left: 1px solid var(--color-border-subtle);
      background: var(--color-background);
    }
    .sheet {
      display: flex;
      flex-direction: column;
      flex: 1;
      min-height: 0;
      overflow: hidden;
    }
    header {
      display: flex;
      align-items: center;
      gap: 4px;
      height: 56px;
      flex: 0 0 56px;
      padding: 0 8px 0 16px;
    }
    .tabs {
      display: flex;
      align-items: center;
      flex: 1;
      min-width: 0;
      gap: 8px;
    }
    .tabs button {
      height: 32px;
      padding: 0 12px;
      border: 0;
      border-radius: var(--radius-pill);
      background: var(--color-chip);
      color: var(--color-text-strong);
      font-size: var(--font-size-body);
      white-space: nowrap;
      transition: background 0.12s;
    }
    .tabs button:hover {
      background: var(--color-chip-hover);
    }
    .tabs button[aria-selected="true"] {
      background: var(--color-text-strong);
      color: var(--color-inverse);
    }
    header .icon-button {
      border-radius: 50%;
    }
    header .icon-button[aria-expanded="true"] {
      color: var(--color-text);
      background: var(--color-chip);
    }
    .body {
      flex: 1;
      min-height: 0;
      overflow-y: auto;
      padding: 0 8px 16px;
    }
    .body:focus-visible {
      outline: none;
    }
    .notice {
      display: flex;
      align-items: center;
      gap: 12px;
      margin: 8px 8px 16px;
      padding: 12px 14px;
      border-radius: var(--radius-control);
      background: var(--color-active);
      color: var(--color-muted);
      font-size: var(--font-size-label);
    }
    .notice .button {
      margin-left: auto;
    }
    spotify-search {
      margin: 8px 8px 16px;
    }
    player-bar {
      border-top: 1px solid var(--color-border-subtle);
    }
    /* The agent's search field opens above the deck while it works there. */
    .agent-stage {
      position: relative;
      z-index: 2;
      flex: none;
      height: 0;
      opacity: 0;
      visibility: hidden;
      transition:
        height 0.28s ease,
        opacity 0.2s ease,
        visibility 0s 0.28s;
    }
    .agent-stage[data-open] {
      height: 56px;
      opacity: 1;
      visibility: visible;
      transition-delay: 0s;
    }
    agent-search {
      margin: 4px 16px 0;
    }
    /* Track table, modelled on Spotify's playlist rows. */
    .list-head,
    .track {
      display: grid;
      grid-template-columns: 24px minmax(0, 1fr) 48px;
      align-items: center;
      gap: 12px;
      padding: 0 8px;
    }
    .list-head {
      position: sticky;
      top: 0;
      z-index: 1;
      height: 36px;
      margin: 4px -8px 4px;
      padding-inline: 16px;
      background: var(--color-background);
      color: var(--color-muted);
      font-size: var(--font-size-label);
    }
    .list-head span:first-child,
    .list-head span:nth-child(3) {
      text-align: right;
    }
    .track {
      height: 56px;
      border-radius: var(--radius-xs);
    }
    .track:hover,
    .track:focus-within {
      background: var(--color-row-hover);
    }
    /* Rows the agent just touched: they land, are rewritten or leave. */
    .track.added {
      animation:
        land 0.34s cubic-bezier(0.2, 0.7, 0.2, 1) backwards,
        touched 1.6s ease-out backwards;
    }
    .track.rewritten {
      animation: touched 1.6s ease-out backwards;
    }
    .track.leaving {
      overflow: hidden;
      pointer-events: none;
      animation: leave 0.34s ease-in forwards;
    }
    .caret {
      display: inline-block;
      width: 1px;
      height: 1.1em;
      margin-left: 1px;
      vertical-align: text-bottom;
      background: var(--color-accent);
    }
    @keyframes land {
      from {
        opacity: 0;
        transform: translateY(-8px);
      }
    }
    @keyframes touched {
      from {
        background: color-mix(in srgb, var(--color-accent) 18%, transparent);
      }
    }
    @keyframes leave {
      to {
        height: 0;
        opacity: 0;
        transform: translateX(16px);
      }
    }
    .index {
      display: grid;
      justify-items: end;
      align-items: center;
      width: 24px;
      height: 32px;
      padding: 0;
      border: 0;
      background: transparent;
      color: var(--color-muted);
      font-size: var(--font-size-track);
      font-variant-numeric: tabular-nums;
    }
    .index .hover {
      display: none;
      color: var(--color-text-strong);
    }
    .track:hover .index:not(:disabled) .rest,
    .index:focus-visible .rest {
      display: none;
    }
    .track:hover .index:not(:disabled) .hover,
    .index:focus-visible .hover {
      display: grid;
    }
    .index:disabled {
      opacity: 1;
    }
    .song {
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 0;
    }
    .song track-cover {
      width: 40px;
      flex-shrink: 0;
    }
    .song div {
      min-width: 0;
      line-height: 1.3;
    }
    .song strong,
    .song span {
      display: block;
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
    }
    .song strong {
      color: var(--color-text-strong);
      font-size: var(--font-size-track);
      font-weight: var(--font-weight-regular);
    }
    .track.active .song strong {
      color: var(--color-play);
    }
    .song span,
    .year {
      color: var(--color-muted);
      font-size: var(--font-size-body);
    }
    .year {
      font-variant-numeric: tabular-nums;
    }
    /* The remove action takes the year's place on hover, so no column is reserved for it. */
    .end {
      position: relative;
      display: flex;
      align-items: center;
      justify-content: flex-end;
    }
    .end .icon-button {
      position: absolute;
      right: -6px;
      opacity: 0;
    }
    .end .icon-button:hover {
      background: transparent;
    }
    .track:hover .year,
    .track:focus-within .year {
      visibility: hidden;
    }
    .track:hover .end .icon-button,
    .track:focus-within .end .icon-button {
      opacity: 1;
    }
    @media (hover: none) {
      .list-head,
      .track {
        grid-template-columns: 24px minmax(0, 1fr) auto;
      }
      .track .year {
        visibility: visible;
      }
      .end .icon-button {
        position: static;
        margin-right: -6px;
        opacity: 1;
        color: var(--color-faint);
      }
    }
    .bars {
      display: flex;
      align-items: flex-end;
      gap: 2px;
      height: 14px;
    }
    .bars i {
      width: 3px;
      height: 100%;
      background: var(--color-play);
      transform-origin: bottom;
      animation: bounce 0.9s ease-in-out infinite;
    }
    .bars i:nth-child(2) {
      animation-delay: -0.3s;
    }
    .bars i:nth-child(3) {
      animation-delay: -0.6s;
    }
    @keyframes bounce {
      0%,
      100% {
        transform: scaleY(0.35);
      }
      50% {
        transform: scaleY(1);
      }
    }
    .undo {
      margin: 12px 16px;
      color: var(--color-muted);
      font-size: var(--font-size-label);
    }
    /* Cards */
    .card-options {
      display: flex;
      align-items: center;
      gap: 10px;
      margin: 8px 8px 18px;
    }
    .card-options label {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      color: var(--color-muted);
      font-size: var(--font-size-body);
    }
    .cards {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
      padding: 0 8px;
    }
    music-card {
      max-width: 300px;
    }
    :host(.expanded) .cards {
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    }
    /* Export */
    .export {
      margin: 8px 8px 12px;
      padding: 20px;
      border: 1px solid var(--color-border);
      border-radius: var(--radius-card);
      background: var(--color-surface);
    }
    .export svg {
      color: var(--color-muted);
    }
    .export h3 {
      margin: 12px 0 4px;
      font-size: var(--font-size-track);
    }
    .export p {
      margin: 0 0 16px;
      color: var(--color-muted);
      font-size: var(--font-size-body);
    }
    .export .button {
      margin-right: 8px;
    }
    .export [role="status"] {
      margin: 14px 0 0;
    }
    iframe {
      width: 100%;
      height: 440px;
      margin-top: 16px;
      border: 0;
      border-radius: var(--radius-control);
    }
    .empty {
      display: grid;
      justify-items: center;
      gap: 6px;
      padding: 64px 24px;
      color: var(--color-muted);
      text-align: center;
    }
    .empty svg {
      margin-bottom: 8px;
      color: var(--color-faint);
    }
    .empty strong {
      color: var(--color-text);
      font-weight: var(--font-weight-medium);
    }
    .empty p {
      max-width: 300px;
      margin: 0;
      font-size: var(--font-size-label);
    }
    @media (max-width: 1000px) {
      :host {
        border-left: 0;
      }
    }
    @media (max-width: 420px) {
      header {
        padding-left: 12px;
      }
      .tabs {
        gap: 6px;
      }
      .list-head {
        display: none;
      }
      player-bar {
        border-top: 0;
      }
      .track {
        grid-template-columns: minmax(0, 1fr) auto;
      }
      .index {
        display: none;
      }
      .cards {
        gap: 10px;
      }
    }
  `;
  private playlistView() {
    const tracks = this.tracks;
    const disabled = this.disabled;
    const stage = this.choreography.stage;
    const canPlay = this.user.spotifyPremium && !this.playback.busy;
    const live =
      !!this.playback.uri && tracks.some((track) => track.spotifyUri === this.playback.uri);
    return html`${!this.user.spotifyConnected ? html`<div class="notice"><span>${msg("Verbinde Spotify für die Wiedergabe und den Playlist-Export.")}</span><button class="button primary" ?disabled=${!!this.oauth.pending} @click=${() => this.oauth.start("spotify-connect")}>${msg("Spotify verbinden")}</button></div>` : nothing}
      ${this.search && !stage ? html`<spotify-search ?disabled=${disabled} @track-select=${(event: CustomEvent<SpotifyTrackResponse>) => this.deck.add(this.sessionId, event.detail)}></spotify-search>` : nothing}
      ${
        tracks.length
          ? html`<div class="list-head" aria-hidden="true">
              <span>#</span><span>${msg("Titel")}</span><span>${msg("Jahr")}</span>
            </div>`
          : nothing
      }
      <div role="list" aria-label=${msg("Songs")}>
        ${repeat(
          tracks,
          (track) => track.id,
          (track, i) => {
            const active = live && track.spotifyUri === this.playback.uri;
            const sounding = active && !this.playback.paused;
            const typed = stage?.rewrite?.trackId === track.id ? stage.rewrite.title : null;
            return html`<div
              class="track ${active ? "active" : ""} ${stage?.marks[track.id] ?? ""}"
              data-key=${track.id}
              role="listitem"
            >
              <button
                class="index"
                aria-label=${sounding ? msg(str`${track.title} pausieren`) : msg(str`${track.title} abspielen`)}
                ?disabled=${!canPlay || !track.spotifyUri}
                @click=${() => this.play(track.spotifyUri)}
              >
                <span class="rest"
                  >${sounding ? html`<span class="bars"><i></i><i></i><i></i></span>` : i + 1}</span
                ><span class="hover"
                  >${sounding ? icon("pause", 16, true) : icon("play", 16, true)}</span
                >
              </button>
              <div class="song">
                <track-cover .src=${track.coverUrl}></track-cover>
                <div>
                  <strong title=${track.title}
                    >${typed ?? track.title}${typed === null ? nothing : html`<i class="caret"></i>`}</strong
                  ><span>${track.artist}</span>
                </div>
              </div>
              <span class="end"
                ><span class="year">${track.year}</span
                ><button
                  class="icon-button"
                  title=${msg("Song entfernen")}
                  aria-label=${msg(str`${track.title} entfernen`)}
                  ?disabled=${disabled}
                  @click=${() => this.deck.remove(this.sessionId, track.id)}
                >
                  ${icon("close", 16)}
                </button></span
              >
            </div>`;
          },
        )}
      </div>
      ${this.curationEvents.filter((event) => event.eventType === "track_removed").map((event) => html`<p class="undo">${msg(str`„${event.trackTitle}“ entfernt.`)} <button class="text-button" ?disabled=${disabled} @click=${() => this.deck.restore(this.sessionId, event.id)}>${msg("Rückgängig")}</button></p>`)}`;
  }
  render() {
    const tracks = this.tracks;
    const disabled = this.disabled;
    const current = this.current;
    const live = !!current && current.spotifyUri === this.playback.uri;
    const note = this.playerNote();
    return html`<div class="sheet">
        <header aria-label=${msg("Deck-Arbeitsbereich")}>
          <div class="tabs" role="tablist" aria-label=${msg("Deckansicht")}>
            ${views.map(
              ({ id, label }) =>
                html`<button
                  id=${`tab-${id}`}
                  role="tab"
                  aria-selected=${this.tab === id}
                  tabindex=${this.tab === id ? "0" : "-1"}
                  aria-controls="deck-content"
                  @keydown=${this.selectTab}
                  @click=${() => (this.tab = id)}
                >
                  ${label()}
                </button>`,
            )}
          </div>
          ${this.deck.exported ? html`<a class="icon-button" href=${this.deck.exported.url} target="_blank" rel="noopener noreferrer" title=${msg("Zur Spotify-Playlist")} aria-label=${msg("Zur Spotify-Playlist")}>${icon("external", 16)}</a>` : nothing}
          ${this.tab === "playlist" ? html`<button class="icon-button" title=${msg("Songs hinzufügen")} aria-label=${msg("Songs hinzufügen")} aria-expanded=${this.search} ?disabled=${disabled} @click=${() => (this.search = !this.search)}>${icon("plus", 18)}</button>` : nothing}
          <button
            class="icon-button"
            aria-label=${this.expanded ? msg("Geteilte Ansicht") : msg("Deck vergrößern")}
            title=${shortcutTitle(this.expanded ? msg("Geteilte Ansicht") : msg("Deck vergrößern"), "expandDeck")}
            aria-keyshortcuts=${shortcutKeys("expandDeck")}
            @click=${() => emit(this, "toggle-expand")}
          >
            ${icon(this.expanded ? "minimize" : "maximize", 15)}
          </button>
          <button
            class="icon-button"
            aria-label=${msg("Deck schließen")}
            title=${shortcutTitle(msg("Deck schließen"), "deck")}
            aria-keyshortcuts=${shortcutKeys("deck")}
            @click=${() => emit(this, "close-panel")}
          >
            ${icon("close", 16)}
          </button>
        </header>
        <div
          class="agent-stage"
          ?data-open=${!!this.choreography.stage?.search && this.tab === "playlist"}
          aria-hidden="true"
        >
          <agent-search .search=${this.agentSearch}></agent-search>
        </div>
        <section
          id="deck-content"
          class="body"
          role="tabpanel"
          tabindex="0"
          aria-labelledby=${`tab-${this.tab}`}
        >
          ${this.deck.error || this.playback.error || this.oauth.error ? html`<p class="error" role="alert">${this.deck.error || this.playback.error || this.oauth.error}</p>` : nothing}
          ${this.tab === "playlist" ? this.playlistView() : nothing}
          ${
            this.tab === "cards"
              ? html`<div class="card-options">
                    <label
                      ><input
                        type="checkbox"
                        .checked=${this.concealed}
                        @change=${(event: Event) => (this.concealed = (event.target as HTMLInputElement).checked)}
                      />
                      ${msg("Auflösung verbergen")}</label
                    >
                  </div>
                  <div class="cards">
                    ${tracks.map(
                      (track, index) =>
                        html`<music-card
                          flippable
                          style=${`--i: ${index}`}
                          .card=${track}
                          ?concealed=${this.concealed}
                        ></music-card>`,
                    )}
                  </div>`
              : nothing
          }
          ${
            this.tab === "export"
              ? html`<div class="export">
                    ${icon("layers", 20)}
                    <h3>${msg("Vom Bildschirm an den Spieltisch.")}</h3>
                    <p>
                      ${msg("Lade dein Deck als druckfertige PDF mit Musik-QR-Codes herunter.")}
                    </p>
                    <button
                      class="button primary"
                      ?disabled=${disabled || !tracks.length}
                      @click=${() => this.deck.pdf(this.sessionId, false)}
                    >
                      ${icon("download", 15)}
                      ${this.deck.pending === "pdf" ? msg("PDF wird erstellt …") : msg("PDF herunterladen")}</button
                    ><button
                      class="button"
                      ?disabled=${disabled || !tracks.length}
                      @click=${() => this.deck.pdf(this.sessionId, true)}
                    >
                      ${msg("Vorschau")}</button
                    >${this.deck.pdfUrl ? html`<iframe title=${msg("PDF-Kartenvorschau")} src=${this.deck.pdfUrl}></iframe>` : nothing}
                  </div>
                  <div class="export">
                    ${icon("music", 20)}
                    <h3>${msg("Deine Songs auf Spotify")}</h3>
                    <p>${msg("Erstelle eine Playlist in deinem verbundenen Spotify-Konto.")}</p>
                    <button
                      class="button"
                      ?disabled=${disabled || !tracks.length || !this.user.spotifyConnected}
                      @click=${() => this.deck.spotify(this.sessionId)}
                    >
                      ${this.deck.pending === "spotify" ? html`${msg("Wird exportiert …")} ${this.deck.retry ? retryLabel(this.deck.retry.attempt, this.deck.retry.maxAttempts) : nothing}` : msg("Nach Spotify exportieren")}</button
                    >${this.deck.exported ? html`<p role="status">${msg("Playlist erstellt.")} <a href=${this.deck.exported.url} target="_blank" rel="noopener noreferrer">${msg("In Spotify öffnen")}</a></p>` : nothing}
                  </div>`
              : nothing
          }
          ${
            !tracks.length && this.tab !== "export"
              ? html`<div class="empty">
                  ${icon("disc", 32)}
                  <strong>${msg("Noch ist die Bühne leer.")}</strong>
                  <p>
                    ${msg("Beschreibe dein Wunschdeck im Chat oder füge einen Song über die Suche hinzu.")}
                  </p>
                </div>`
              : nothing
          }
        </section>
      </div>
      ${
        current
          ? html`<player-bar
              .track=${{ title: current.title, artist: current.artist, coverUrl: current.coverUrl }}
              ?playing=${live && !this.playback.paused}
              ?live=${live}
              ?disabled=${!this.user.spotifyPremium}
              ?busy=${this.playback.busy}
              ?hasPrevious=${!!this.step(-1)}
              ?hasNext=${!!this.step(1)}
              .position=${this.playback.position}
              .duration=${this.playback.duration}
              .volume=${this.playback.volume}
              .note=${note}
              @player-toggle=${() => this.play(current.spotifyUri)}
              @player-previous=${() => this.play(this.step(-1))}
              @player-next=${() => this.play(this.step(1))}
              @player-seek=${(event: CustomEvent<number>) => this.playback.seek(event.detail)}
              @player-volume=${(event: CustomEvent<number>) => this.playback.setVolume(event.detail)}
            ></player-bar>`
          : nothing
      }`;
  }
}
