import { css, html, LitElement, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { spotifyDisconnect } from "@api/generated/spotify";
import { deleteMe, getDeleteInformation, type UserMeResponse } from "@api/generated/users";
import { pageStyles } from "@shared/styles/page";
import { emit, errorMessage } from "@shared/events";
import { OAuthController } from "@features/auth/oauth-controller";

@customElement("settings-page")
export class SettingsPage extends LitElement {
  @property({ attribute: false }) user!: UserMeResponse;
  @state() private error = "";
  @state() private pending = false;
  @state() private deleteInfo = "";
  private oauth = new OAuthController(this, async () => {
    emit(this, "user-refresh");
  });
  private async disconnect(): Promise<void> {
    this.pending = true;
    try {
      await spotifyDisconnect();
      emit(this, "user-refresh");
    } catch (error) {
      this.error = errorMessage(error);
    } finally {
      this.pending = false;
    }
  }
  private async prepareDelete(): Promise<void> {
    this.pending = true;
    try {
      const info = await getDeleteInformation();
      this.deleteInfo = `${info.sessionCount} Decks mit ihren Unterhaltungen werden zusammen mit deinem Konto gelöscht.`;
      this.renderRoot.querySelector("dialog")?.showModal();
    } catch (error) {
      this.error = errorMessage(error);
    } finally {
      this.pending = false;
    }
  }
  private async removeAccount(): Promise<void> {
    this.pending = true;
    try {
      await deleteMe();
      emit(this, "user-refresh");
    } catch (error) {
      this.error = errorMessage(error);
    } finally {
      this.pending = false;
    }
  }
  static styles = css`
    ${pageStyles} :host {
      display: block;
      max-width: 760px;
      width: 100%;
      margin: 0 auto;
      padding: 48px 28px;
      overflow-y: auto;
    }
    h1 {
      font-size: 28px;
      margin: 0 0 32px;
    }
    section {
      margin-bottom: 32px;
      border-top: 1px solid var(--color-border);
    }
    h2 {
      font-size: 13px;
      color: var(--color-muted);
      margin: 22px 0;
    }
    .row {
      display: flex;
      gap: 20px;
      align-items: center;
      justify-content: space-between;
      padding: 12px 0;
    }
    .row p {
      margin: 4px 0;
      font-size: 12px;
      color: var(--color-muted);
    }
    .row strong {
      font-size: 14px;
    }
    pre {
      white-space: pre-wrap;
      font-size: 11px;
      color: var(--color-muted);
    }
    .danger {
      color: var(--color-error);
    }
  `;
  render() {
    return html`<h1>Einstellungen</h1>
      ${this.error || this.oauth.error ? html`<p class="error" role="alert">${this.error || this.oauth.error}</p>` : nothing}
      <section>
        <h2>Dein Konto</h2>
        <div class="row">
          <div>
            <strong>${this.user.name}</strong>
            <p>Deine Decks werden in deinem Konto gespeichert.</p>
          </div>
          <button class="button" @click=${() => emit(this, "sign-out")}>Abmelden</button>
        </div>
      </section>
      <section>
        <h2>Musik & Wiedergabe</h2>
        <div class="row">
          <div>
            <strong>Spotify</strong>
            <p>
              ${this.user.spotifyConnected ? (this.user.spotifyPremium ? "Verbunden · Premium" : "Verbunden · Standard") : "Verbinde dein Konto für Playlist-Exporte."}
            </p>
          </div>
          <button
            class="button"
            ?disabled=${this.pending || !!this.oauth.pending}
            @click=${() => (this.user.spotifyConnected ? this.disconnect() : this.oauth.start("spotify-connect"))}
          >
            ${this.user.spotifyConnected ? "Trennen" : "Verbinden"}
          </button>
        </div>
      </section>
      <section>
        <h2>Kontoverwaltung</h2>
        <div class="row">
          <div>
            <strong>Konto löschen</strong>
            <p>Entfernt dein Konto und die zugehörigen Daten dauerhaft.</p>
          </div>
          <button class="button danger" ?disabled=${this.pending} @click=${this.prepareDelete}>
            Konto löschen
          </button>
        </div>
      </section>
      <dialog aria-label="Konto endgültig löschen">
        <h2>Konto endgültig löschen?</h2>
        <p>Diese Aktion kann nicht rückgängig gemacht werden.</p>
        <p>${this.deleteInfo}</p>
        <div class="actions">
          <button
            class="button"
            ?disabled=${this.pending}
            @click=${() => this.renderRoot.querySelector("dialog")?.close()}
          >
            Abbrechen</button
          ><button class="button danger" ?disabled=${this.pending} @click=${this.removeAccount}>
            Endgültig löschen
          </button>
        </div>
      </dialog>`;
  }
}
