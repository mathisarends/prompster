import { msg, localized } from "@lit/localize";
import { css, html, LitElement } from "lit";
import { customElement, property } from "lit/decorators.js";
import { workspaceStyles } from "@shared/styles/workspace";

@customElement("human-message")
@localized()
export class HumanMessage extends LitElement {
  @property() text = "";
  static styles = css`
    ${workspaceStyles} :host {
      display: flex;
      justify-content: flex-end;
    }
    p {
      max-width: min(80%, 560px);
      margin: 0;
      padding: 10px 16px;
      border-radius: var(--radius-bubble);
      background: var(--color-raised);
      color: var(--color-text);
      font-size: var(--font-size-chat);
      line-height: 1.6;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }
  `;
  render() {
    return html`<p aria-label=${msg("Dein Briefing")}>${this.text}</p>`;
  }
}
