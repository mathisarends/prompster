import { msg, localized } from "@lit/localize";
import { getLocale } from "@shared/i18n";
import { deleteAccountDescription } from "@shared/i18n/messages";
import { css, html, LitElement, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { spotifyDisconnect } from "@api/generated/spotify";
import { deleteMe, getDeleteInformation, type UserMeResponse } from "@api/generated/users";
import { pageStyles } from "@shared/styles/page";
import { emit, errorMessage } from "@shared/events";
import { OAuthController } from "@features/auth/oauth-controller";
import "@shared/ui/language-select";

@customElement("settings-page")
@localized()
export class SettingsPage extends LitElement {
  @property({ attribute: false }) user!: UserMeResponse;
  @state() private error = "";
  @state() private pending = false;
  @state() private deleteCount = 0;
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
      this.deleteCount = info.sessionCount;
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
    ${pageStyles}
    :host {
      display: block;
      overflow-y: auto;
    }
    .page {
      width: min(100%, var(--content-width));
      margin: 0 auto;
      padding: 56px 24px 64px;
    }
    h1 {
      margin: 0 0 32px;
      font-size: var(--font-size-title);
    }
    section {
      margin-bottom: 28px;
    }
    h2 {
      margin: 0 0 8px 4px;
      color: var(--color-muted);
      font-size: var(--font-size-label);
      font-weight: var(--font-weight-medium);
    }
    .card {
      border: 1px solid var(--color-border);
      border-radius: var(--radius-card);
      background: var(--color-surface);
    }
    .row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
      min-height: 64px;
      padding: 12px 16px;
    }
    .row + .row {
      border-top: 1px solid var(--color-border);
    }
    .row strong {
      display: block;
      color: var(--color-text-strong);
      font-weight: var(--font-weight-medium);
    }
    .row p {
      margin: 2px 0 0;
      color: var(--color-muted);
      font-size: var(--font-size-label);
    }
    .button {
      flex-shrink: 0;
    }
    .account {
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 0;
    }
    .avatar {
      display: grid;
      place-items: center;
      width: 36px;
      height: 36px;
      flex-shrink: 0;
      border-radius: 50%;
      background: var(--color-control);
      font-weight: var(--font-weight-medium);
    }
    .connected {
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    .connected::before {
      content: "";
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--color-play);
    }
    @media (max-width: 560px) {
      .page {
        padding: 32px 16px 48px;
      }
      .row {
        flex-wrap: wrap;
      }
    }
  `;
  render() {
    const spotify = this.user.spotifyConnected
      ? this.user.spotifyPremium
        ? msg("Verbunden · Premium")
        : msg("Verbunden · Standard")
      : msg("Verbinde dein Konto für Playlist-Exporte.");
    return html`<div class="page">
      <h1>${msg("Einstellungen")}</h1>
      ${this.error || this.oauth.error ? html`<p class="error" role="alert">${this.error || this.oauth.error}</p>` : nothing}
      <section>
        <h2>${msg("Allgemein")}</h2>
        <div class="card">
          <div class="row">
            <div>
              <strong>${msg("Sprache")}</strong>
              <p>${msg("Sprache der Oberfläche und der Spracheingabe.")}</p>
            </div>
            <language-select></language-select>
          </div>
        </div>
      </section>
      <section>
        <h2>${msg("Dein Konto")}</h2>
        <div class="card">
          <div class="row">
            <div class="account">
              <span class="avatar" aria-hidden="true"
                >${this.user.name.slice(0, 1).toLocaleUpperCase(getLocale())}</span
              >
              <div>
                <strong>${this.user.name}</strong>
                <p>${msg("Deine Decks werden in deinem Konto gespeichert.")}</p>
              </div>
            </div>
            <button class="button" @click=${() => emit(this, "sign-out")}>
              ${msg("Abmelden")}
            </button>
          </div>
        </div>
      </section>
      <section>
        <h2>${msg("Musik & Wiedergabe")}</h2>
        <div class="card">
          <div class="row">
            <div>
              <strong>Spotify</strong>
              <p class=${this.user.spotifyConnected ? "connected" : ""}>${spotify}</p>
            </div>
            <button
              class="button"
              ?disabled=${this.pending || !!this.oauth.pending}
              @click=${() => (this.user.spotifyConnected ? this.disconnect() : this.oauth.start("spotify-connect"))}
            >
              ${this.user.spotifyConnected ? msg("Trennen") : msg("Verbinden")}
            </button>
          </div>
        </div>
      </section>
      <section>
        <h2>${msg("Kontoverwaltung")}</h2>
        <div class="card">
          <div class="row">
            <div>
              <strong>${msg("Konto löschen")}</strong>
              <p>${msg("Entfernt dein Konto und die zugehörigen Daten dauerhaft.")}</p>
            </div>
            <button class="button danger" ?disabled=${this.pending} @click=${this.prepareDelete}>
              ${msg("Konto löschen")}
            </button>
          </div>
        </div>
      </section>
      <dialog aria-label=${msg("Konto endgültig löschen")}>
        <h2>${msg("Konto endgültig löschen?")}</h2>
        <p>${msg("Diese Aktion kann nicht rückgängig gemacht werden.")}</p>
        <p>${deleteAccountDescription(this.deleteCount)}</p>
        <div class="actions">
          <button
            class="button"
            ?disabled=${this.pending}
            @click=${() => this.renderRoot.querySelector("dialog")?.close()}
          >
            ${msg("Abbrechen")}</button
          ><button class="button danger" ?disabled=${this.pending} @click=${this.removeAccount}>
            ${msg("Endgültig löschen")}
          </button>
        </div>
      </dialog>
    </div>`;
  }
}
