import { msg, localized } from "@lit/localize";
import { css, html, LitElement, nothing } from "lit";
import { customElement, property } from "lit/decorators.js";
import { pageStyles } from "@shared/styles/page";
import { emit } from "@shared/events";
import "@shared/ui/brand-mark";
import "@features/deck/components/music-card";
import { exampleCards } from "@features/chat/examples";
import { OAuthController } from "./oauth-controller";

@customElement("login-page")
@localized()
export class LoginPage extends LitElement {
  @property({ attribute: false }) onAuthenticated: () => Promise<void> = async () => {};
  @property() connectionError = "";
  private oauth = new OAuthController(this, () => this.onAuthenticated());
  static styles = css`
    ${pageStyles}
    :host {
      display: flex;
      flex-direction: column;
      min-height: 100dvh;
      background: var(--color-background);
    }
    header {
      display: flex;
      align-items: center;
      height: 64px;
      padding: 0 24px;
    }
    brand-mark {
      --brand-mark-size: 24px;
      font-size: var(--font-size-chat);
    }
    main {
      display: grid;
      place-items: center;
      flex: 1;
      padding: 24px 24px 64px;
    }
    section {
      width: min(100%, 380px);
      text-align: center;
    }
    .cards {
      display: flex;
      justify-content: center;
      height: 132px;
      margin-bottom: 36px;
    }
    music-card {
      width: 100px;
      flex-shrink: 0;
      border-radius: var(--radius-xs);
      overflow: hidden;
      box-shadow: var(--shadow-panel);
    }
    music-card:first-child {
      transform: rotate(-12deg) translate(16px, 12px);
    }
    music-card:nth-child(2) {
      z-index: 1;
    }
    music-card:last-child {
      transform: rotate(12deg) translate(-16px, 12px);
    }
    h1 {
      margin: 0;
      font-size: var(--font-size-display);
      font-weight: var(--font-weight-medium);
      line-height: 1.15;
    }
    .intro {
      margin: 12px 0 28px;
      color: var(--color-muted);
      text-wrap: balance;
    }
    .button {
      width: 100%;
      min-height: 42px;
      margin-top: 8px;
      font-size: var(--font-size-body);
    }
    .error {
      margin-top: 16px;
      text-align: left;
    }
    .small {
      margin: 28px 0 0;
      color: var(--color-faint);
      font-size: var(--font-size-caption);
    }
  `;
  render() {
    document.title = `${msg("Dein Deckstudio")} · Prompster`;
    return html`<header><brand-mark></brand-mark></header>
      <main>
        <section>
          <div class="cards" aria-label=${msg("Beispielkarten")}>
            ${exampleCards.map((card, i) => html`<music-card .card=${card} .index=${i}></music-card>`)}
          </div>
          <h1>${msg(html`Aus Lieblingssongs<br />werden Spieleabende.`)}</h1>
          <p class="intro">
            ${msg("Beschreibe deine Musikidee. Prompster findet die passenden Songs und macht daraus dein persönliches Musik-Kartendeck.")}
          </p>
          <button
            class="button primary"
            ?disabled=${!!this.oauth.pending}
            @click=${() => this.oauth.start("spotify")}
          >
            ${this.oauth.pending === "spotify" ? msg("Spotify-Anmeldung läuft …") : msg("Mit Spotify fortfahren")}
          </button>
          <button
            class="button"
            ?disabled=${!!this.oauth.pending}
            @click=${() => this.oauth.start("google")}
          >
            ${this.oauth.pending === "google" ? msg("Google-Anmeldung läuft …") : msg("Mit Google fortfahren")}
          </button>
          ${this.oauth.error ? html`<p class="error" role="alert">${this.oauth.error}</p>` : nothing}
          ${
            this.connectionError
              ? html`<p class="error" role="alert">
                  ${this.connectionError}
                  <button class="text-button" @click=${() => emit(this, "retry-auth")}>
                    ${msg("Verbindung erneut prüfen")}
                  </button>
                </p>`
              : nothing
          }
          <p class="small">${msg("Musik entdecken · Karten gestalten · Gemeinsam spielen")}</p>
        </section>
      </main>`;
  }
}
