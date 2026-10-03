import { css, html, LitElement } from "lit";
import { customElement } from "lit/decorators.js";
import { icon } from "./icons";

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
      display: grid;
      place-items: center;
      width: 30px;
      height: 34px;
      border-radius: 8px;
      color: var(--color-on-accent);
      background: var(--color-accent);
      transform: rotate(-8deg);
    }
    svg {
      transform: rotate(8deg);
    }
  `;
  render() {
    return html`<span class="mark">${icon("music", 19)}</span
      ><span>prompster<span aria-hidden="true">.</span></span>`;
  }
}
