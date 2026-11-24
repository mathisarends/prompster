import { localized, msg, str } from "@lit/localize";
import { css, html, LitElement } from "lit";
import { customElement, property } from "lit/decorators.js";
import { pageStyles } from "@shared/styles/page";
import { icon } from "@shared/ui/icons";
import { emit } from "@shared/events";
import type { ChatAttachment } from "./attachments/attachment-types";

@customElement("chat-attachments")
@localized()
export class ChatAttachments extends LitElement {
  @property({ attribute: false }) items: ChatAttachment[] = [];
  @property({ type: Boolean }) disabled = false;
  static styles = css`
    ${pageStyles}
    :host {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      padding-bottom: 10px;
    }
    .chip {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      max-width: 100%;
      height: 28px;
      padding: 0 2px 0 10px;
      border-radius: var(--radius-control);
      background: var(--color-chip);
      color: var(--color-text);
      font-size: var(--font-size-caption);
    }
    .chip > svg {
      color: var(--color-muted);
    }
    .name {
      max-width: 180px;
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
    }
    .icon-button {
      width: 24px;
      height: 24px;
      border-radius: var(--radius-sm);
    }
  `;
  render() {
    return html`${this.items.map((item) => html`<span class="chip">${icon(item.kind === "image" ? "layers" : "music", 14)}<span class="name">${item.title}</span><button class="icon-button" aria-label=${msg(str`${item.title} entfernen`)} ?disabled=${this.disabled} @click=${() => emit(this, "attachment-remove", item.id)}>${icon("close", 13)}</button></span>`)}`;
  }
}
