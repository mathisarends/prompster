import { css, html, LitElement, nothing } from "lit";
import { customElement, state } from "lit/decorators.js";
import { localized, msg } from "@lit/localize";
import { getLocale, setLocale } from "@shared/i18n";
import { pageStyles } from "@shared/styles/page";

@customElement("language-select")
@localized()
export class LanguageSelect extends LitElement {
  @state() private pending = false;
  @state() private failed = false;

  private async change(event: Event): Promise<void> {
    const select = event.currentTarget as HTMLSelectElement;
    this.pending = true;
    this.failed = false;
    try {
      await setLocale(select.value);
    } catch {
      this.failed = true;
    } finally {
      this.pending = false;
      select.value = getLocale();
    }
  }

  static styles = css`
    ${pageStyles}
    :host {
      display: block;
    }
    label {
      display: flex;
      align-items: center;
      gap: 12px;
      color: var(--color-muted);
      font-size: 12px;
    }
    select {
      width: auto;
      min-width: 112px;
      padding: 8px 12px;
    }
    .error {
      max-width: 260px;
      font-size: 12px;
    }
  `;

  render() {
    return html`<label>
        ${msg("Sprache")}
        <select
          class="input"
          .value=${getLocale()}
          ?disabled=${this.pending}
          @change=${this.change}
        >
          <option value="de" lang="de">Deutsch</option>
          <option value="en" lang="en">English</option>
        </select>
      </label>
      ${this.failed ? html`<p class="error" role="alert">${msg("Die Sprache konnte nicht geladen werden. Bitte erneut versuchen.")}</p>` : nothing}`;
  }
}
