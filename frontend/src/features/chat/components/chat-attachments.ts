import { css, html, LitElement } from "lit";
import { customElement, property } from "lit/decorators.js";
import { pageStyles } from "@shared/styles/page";
import { icon } from "@shared/ui/icons";
import { emit } from "@shared/events";
import type { ChatAttachment } from "./attachments/attachment-types";

@customElement("chat-attachments")
export class ChatAttachments extends LitElement {
  @property({ attribute: false }) items: ChatAttachment[] = [];
  @property({ type: Boolean }) disabled = false;
  static styles = css`
    ${pageStyles} :host {
      display: flex;
      gap: 7px;
      flex-wrap: wrap;
      padding-bottom: 10px;
    }
    .chip {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      padding: 4px 6px 4px 10px;
      border: 1px solid var(--color-border-strong);
      border-radius: 10px;
      font-size: 11px;
      max-width: 100%;
    }
    .name {
      max-width: 170px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .icon-button {
      width: 24px;
      height: 24px;
    }
  `;
  render() {
    return html`${this.items.map((item) => html`<span class="chip">${icon(item.kind === "image" ? "layers" : "music", 14)}<span class="name">${item.title}</span><button class="icon-button" aria-label=${`${item.title} entfernen`} ?disabled=${this.disabled} @click=${() => emit(this, "attachment-remove", item.id)}>${icon("close", 13)}</button></span>`)}`;
  }
}
