import { css, html, LitElement } from "lit";
import { customElement, property } from "lit/decorators.js";
import { workspaceStyles } from "@shared/styles/workspace";
import { icon } from "@shared/ui/icons";
import "./chat-markdown";

@customElement("assistant-message")
export class AssistantMessage extends LitElement {
  @property() text = "";
  static styles = css`
    ${workspaceStyles} :host {
      display: block;
    }
    .name {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 500;
    }
    svg {
      color: var(--color-accent);
    }
    p {
      color: var(--color-muted);
      line-height: 1.8;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }
  `;
  render() {
    return html`<div class="name">${icon("sparkles", 17)} Prompster</div>
      <chat-markdown style="margin-top: 14px" .text=${this.text}></chat-markdown><slot></slot>`;
  }
}
