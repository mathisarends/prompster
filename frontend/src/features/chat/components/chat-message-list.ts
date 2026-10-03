import { css, html, LitElement, nothing, type PropertyValues } from "lit";
import { customElement, property, query } from "lit/decorators.js";
import { repeat } from "lit/directives/repeat.js";
import { pageStyles } from "@shared/styles/page";
import { icon } from "@shared/ui/icons";
import { emit } from "@shared/events";
import "@chat";
import type { ChatEntry } from "../state/chat-reducer";
import { toToolCallItems } from "../state/chat-reducer";

@customElement("chat-message-list")
export class ChatMessageList extends LitElement {
  @property({ attribute: false }) entries: ChatEntry[] = [];
  @property({ type: Boolean }) pending = false;
  @query(".scroll") private scroller!: HTMLElement;
  private stick = true;
  protected updated(changed: PropertyValues): void {
    if (this.stick && (changed.has("entries") || changed.has("pending"))) {
      this.scroller.scrollTop = this.scroller.scrollHeight;
    }
  }
  static styles = css`
    ${pageStyles}
    :host {
      display: flex;
      flex: 1;
      min-height: 0;
    }
    .scroll {
      width: 100%;
      overflow-y: auto;
      padding: 28px max(22px, calc((100% - 740px) / 2));
    }
    .entry {
      margin-bottom: 30px;
    }
    details {
      padding: 10px 0;
      color: var(--color-muted);
      font-size: 12px;
    }
    summary {
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .tool {
      margin: 10px 0;
      padding: 10px 14px;
      border-left: 1px solid var(--color-border);
    }
    .tool strong {
      color: var(--color-text);
      font-size: 12px;
    }
    .tool p {
      margin: 4px 0;
      white-space: pre-wrap;
    }
    .pending {
      display: flex;
      align-items: center;
      gap: 9px;
      font-size: 12px;
      color: var(--color-muted);
    }
    .pending svg {
      color: var(--color-accent);
    }
    .attachments {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: flex-end;
      margin-bottom: 10px;
    }
    .attachment {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      font-size: 11px;
      padding: 7px 10px;
      border: 1px solid var(--color-border);
      border-radius: 9px;
    }
    img {
      max-width: 170px;
      max-height: 140px;
      border-radius: 10px;
    }
  `;
  render() {
    return html`<div
      class="scroll"
      role="log"
      aria-label="Unterhaltung"
      aria-live="polite"
      @scroll=${() => {
        this.stick =
          this.scroller.scrollHeight - this.scroller.clientHeight - this.scroller.scrollTop < 100;
      }}
    >
      ${repeat(
        this.entries,
        (entry) => entry.id,
        (entry) =>
          html`<div class="entry">
            ${
              entry.kind === "user_message"
                ? html`<div class="attachments">
                      ${(entry.imageAttachments ?? []).map((url) => (/^https?:/.test(url) || url.startsWith("/") ? html`<a href=${url} target="_blank" rel="noopener noreferrer"><img src=${url} alt="Angehängtes Bild" loading="lazy" /></a>` : nothing))}${entry.attachments?.map((item) => html`<span class="attachment">${icon("music", 14)}${item.title}</span>`)}${entry.userCurationEvents?.map((event) => html`<span class="attachment">${event.eventType === "track_added" ? "+" : "−"} ${event.trackTitle}</span>`)}
                    </div>
                    <human-message .text=${entry.content}></human-message>`
                : entry.kind === "assistant_message"
                  ? html`<assistant-message .text=${entry.content}></assistant-message>`
                  : html`<details>
                      <summary>
                        ${icon("sparkles", 15)} ${entry.calls.length} Recherche-Schritte
                      </summary>
                      ${toToolCallItems(entry).map(
                        (call) =>
                          html`<div class="tool">
                            <strong>${call.text}</strong>
                            <p>
                              ${call.status === "failed" ? "Fehlgeschlagen" : call.status === "completed" ? "Abgeschlossen" : "In Arbeit"}${call.retry ? ` · Versuch ${call.retry.attempt}/${call.retry.maxAttempts}` : ""}
                            </p>
                            ${call.detail ? html`<p>${call.detail}</p>` : nothing}${call.resultItems?.map((item) => html`<p>${item.title}${item.artist ? ` · ${item.artist}` : ""}</p>`)}
                          </div>`,
                      )}
                    </details>`
            }
          </div>`,
      )}${this.pending ? html`<p class="pending" role="status">${icon("sparkles", 16)} Prompster arbeitet an deinem Deck …</p>` : nothing}<slot
      ></slot>
    </div>`;
  }
}
