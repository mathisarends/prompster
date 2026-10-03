import { css, html, LitElement } from "lit";
import { customElement, property } from "lit/decorators.js";
import { workspaceStyles } from "@shared/styles/workspace";

@customElement("human-message")
export class HumanMessage extends LitElement {
  @property() text = "";
  static styles = css`
    ${workspaceStyles} :host {
      display: flex;
      justify-content: flex-end;
    }
    p {
      max-width: 85%;
      margin: 0;
      padding: 14px 18px;
      border-radius: 20px 20px 5px 20px;
      background: var(--color-panel);
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }
  `;
  render() {
    return html`<p aria-label="Dein Briefing">${this.text}</p>`;
  }
}
