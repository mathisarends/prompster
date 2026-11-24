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
      display: grid;
      justify-items: end;
      gap: 8px;
    }
    select {
      width: auto;
      min-width: 132px;
      height: 34px;
      padding: 0 12px;
    }
    .error {
      max-width: 260px;
      margin: 0;
      font-size: var(--font-size-caption);
    }
  `;

  render() {
    return html`<select
        class="input"
        aria-label=${msg("Sprache")}
        .value=${getLocale()}
        ?disabled=${this.pending}
        @change=${this.change}
      >
        <option value="de" lang="de">Deutsch</option>
        <option value="en" lang="en">English</option>
      </select>
      ${this.failed ? html`<p class="error" role="alert">${msg("Die Sprache konnte nicht geladen werden. Bitte erneut versuchen.")}</p>` : nothing}`;
  }
}
