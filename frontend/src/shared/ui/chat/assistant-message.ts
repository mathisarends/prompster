import { css, html, LitElement } from "lit";
import { customElement, property } from "lit/decorators.js";
import { workspaceStyles } from "@shared/styles/workspace";
import "./chat-markdown";

@customElement("assistant-message")
export class AssistantMessage extends LitElement {
  @property() text = "";
  static styles = css`
    ${workspaceStyles} :host {
      display: block;
    }
    p {
      color: var(--color-muted);
      line-height: 1.8;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }
  `;
  render() {
    return html`<chat-markdown .text=${this.text}></chat-markdown><slot></slot>`;
  }
}
