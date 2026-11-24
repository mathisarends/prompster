import { css, html, LitElement } from "lit";
import { customElement } from "lit/decorators.js";

@customElement("brand-mark")
export class BrandMark extends LitElement {
  static styles = css`
    :host {
      display: inline-flex;
      align-items: center;
      gap: 9px;
      font-family: var(--font-sans);
      font-size: 18px;
      font-weight: var(--font-weight-medium);
      letter-spacing: -0.6px;
    }
    .mark {
      width: var(--brand-mark-size, 36px);
      height: var(--brand-mark-size, 36px);
      flex-shrink: 0;
    }
  `;
  render() {
    return html`<img class="mark" src="/prompster-mark.svg" alt="" width="36" height="36" />
      <span>prompster<span aria-hidden="true">.</span></span>`;
  }
}
