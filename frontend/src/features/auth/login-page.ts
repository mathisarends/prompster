import { msg, localized } from "@lit/localize";
import { css, html, LitElement, nothing } from "lit";
import { customElement, property } from "lit/decorators.js";
import { pageStyles } from "@shared/styles/page";
import { emit } from "@shared/events";
import "@shared/ui/brand-mark";
import "@shared/ui/language-select";
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
      display: block;
      min-height: 100dvh;
    }
    header {
      height: 90px;
      display: flex;
      align-items: center;
      padding: 0 5vw;
      justify-content: space-between;
    }
    main {
      min-height: calc(100dvh - 150px);
      display: grid;
      grid-template-columns: 1fr 1fr;
      align-items: center;
      max-width: 1100px;
      margin: auto;
      padding: 32px;
      gap: 100px;
    }
    h1 {
      font-size: clamp(35px, 4vw, 52px);
      line-height: 1.07;
      letter-spacing: -2px;
      margin: 20px 0;
    }
    .intro {
      color: var(--color-muted);
      line-height: 1.8;
      margin: 0 0 30px;
    }
    .button {
      width: 100%;
      margin-top: 10px;
      min-height: 46px;
    }
    .small {
      font-size: 11px;
      color: var(--color-muted);
      margin-top: 22px;
      text-align: center;
    }
    .art {
      position: relative;
      display: flex;
      justify-content: center;
      align-items: center;
      height: 370px;
    }
    music-card {
      width: 175px;
      position: absolute;
    }
    music-card:first-child {
      transform: translate(-110px, 10px) rotate(-16deg);
    }
    music-card:nth-child(2) {
      transform: translateY(-20px);
      z-index: 2;
    }
    music-card:last-child {
      transform: translate(110px, 10px) rotate(16deg);
    }
    .caption {
      text-align: center;
      color: var(--color-muted);
      font: 10px var(--font-mono);
      letter-spacing: 2px;
    }
    @media (max-width: 850px) {
      main {
        grid-template-columns: 1fr;
        max-width: 480px;
        gap: 20px;
        padding-top: 30px;
      }
      .visual {
        display: none;
      }
    }
  `;
  render() {
    document.title = `${msg("Dein Deckstudio")} · Prompster`;
    return html`<header><brand-mark></brand-mark><language-select></language-select></header>
      <main>
        <section>
          <p class="eyebrow">${msg("DEIN SOUNDTRACK. DEIN SPIEL.")}</p>
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
              ? html`<p class="error" role="alert">${this.connectionError}</p>
                  <button class="text-button" @click=${() => emit(this, "retry-auth")}>
                    ${msg("Verbindung erneut prüfen")}
                  </button>`
              : nothing
          }
          <p class="small">${msg("Musik entdecken · Karten gestalten · Gemeinsam spielen")}</p>
        </section>
        <section class="visual" aria-label=${msg("Beispielkarten")}>
          <div class="art">
            ${exampleCards.map((card, i) => html`<music-card .card=${card} .index=${i}></music-card>`)}
          </div>
          <p class="caption">${msg("JEDER HIT HAT SEINE ZEIT.")}</p>
        </section>
      </main>`;
  }
}
