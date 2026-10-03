import { css, html, LitElement } from "lit";
import { customElement } from "lit/decorators.js";

@customElement("brand-mark")
export class BrandMark extends LitElement {
  static styles = css`
    :host {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      font: 500 18px var(--font-sans);
      letter-spacing: -0.6px;
    }
    .mark {
      width: 36px;
      height: 36px;
      flex-shrink: 0;
    }
  `;
  render() {
    return html`<img class="mark" src="/prompster-mark.svg" alt="" width="36" height="36" />
      <span>prompster<span aria-hidden="true">.</span></span>`;
  }
}
