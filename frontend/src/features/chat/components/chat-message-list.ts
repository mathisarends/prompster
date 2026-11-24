import { msg, localized } from "@lit/localize";
import { researchStepCount, retryLabel } from "@shared/i18n/messages";
import { css, html, LitElement, nothing, type PropertyValues } from "lit";
import { customElement, property, query } from "lit/decorators.js";
import { repeat } from "lit/directives/repeat.js";
import { pageStyles } from "@shared/styles/page";
import { icon } from "@shared/ui/icons";
import { emit } from "@shared/events";
import "@chat";
import type { RunStatus } from "@/api/session-streams";
import type { ChatEntry } from "../state/chat-reducer";
import { toToolCallItems } from "../state/chat-reducer";

@customElement("chat-message-list")
@localized()
export class ChatMessageList extends LitElement {
  @property({ attribute: false }) entries: ChatEntry[] = [];
  @property({ type: Boolean }) pending = false;
  @property({ attribute: false }) runStatus: RunStatus = "running";
  @query(".scroll") private scroller!: HTMLElement;
  private stick = true;
  protected updated(changed: PropertyValues): void {
    if (this.stick && (changed.has("entries") || changed.has("pending"))) {
      this.scroller.scrollTop = this.scroller.scrollHeight;
    }
  }
  private pendingStatus() {
    switch (this.runStatus) {
      case "paused":
        return html`<p class="pending" role="status">
          ${icon("pause", 16)} ${msg("Pausiert. Setze fort, wenn du so weit bist.")}
        </p>`;
      case "compacting":
        return html`<p class="pending" role="status">
          ${icon("layers", 16)} ${msg("Prompster fasst den bisherigen Verlauf zusammen …")}
        </p>`;
      default:
        return html`<p class="pending" role="status">
          ${icon("sparkles", 16)} ${msg("Prompster arbeitet an deinem Deck …")}
        </p>`;
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
      padding: 24px max(24px, calc((100% - var(--content-width)) / 2));
    }
    .entry {
      margin-bottom: 32px;
    }
    /* Research steps collapse into one quiet line, like T3's tool calls. */
    details {
      color: var(--color-muted);
      font-size: var(--font-size-label);
    }
    summary {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 4px 8px 4px 0;
      border-radius: var(--radius-sm);
      cursor: pointer;
      list-style: none;
    }
    summary::-webkit-details-marker {
      display: none;
    }
    summary:hover {
      color: var(--color-text);
    }
    summary svg {
      color: var(--color-faint);
    }
    .tool {
      margin: 8px 0 0 7px;
      padding: 2px 0 2px 16px;
      border-left: 1px solid var(--color-border);
    }
    .tool strong {
      color: var(--color-text);
      font-weight: var(--font-weight-medium);
    }
    .tool p {
      margin: 2px 0 0;
      color: var(--color-faint);
      font-size: var(--font-size-caption);
      white-space: pre-wrap;
    }
    .pending {
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--color-muted);
      font-size: var(--font-size-label);
    }
    .pending svg {
      color: var(--color-accent);
      animation: glow 1.6s ease-in-out infinite;
    }
    @keyframes glow {
      50% {
        opacity: 0.35;
      }
    }
    .attachments {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      justify-content: flex-end;
      margin-bottom: 8px;
    }
    .attachment {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      border-radius: var(--radius-pill);
      background: var(--color-chip);
      color: var(--color-muted);
      font-size: var(--font-size-caption);
    }
    img {
      max-width: 170px;
      max-height: 140px;
      border-radius: var(--radius-control);
    }
  `;
  render() {
    return html`<div
      class="scroll"
      role="log"
      aria-label=${msg("Unterhaltung")}
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
                      ${(entry.imageAttachments ?? []).map((url) => (/^https?:/.test(url) || url.startsWith("/") ? html`<a href=${url} target="_blank" rel="noopener noreferrer"><img src=${url} alt=${msg("Angehängtes Bild")} loading="lazy" /></a>` : nothing))}${entry.attachments?.map((item) => html`<span class="attachment">${icon("music", 14)}${item.title}</span>`)}${entry.userCurationEvents?.map((event) => html`<span class="attachment">${event.eventType === "track_added" ? "+" : "−"} ${event.trackTitle}</span>`)}
                    </div>
                    <human-message .text=${entry.content}></human-message>`
                : entry.kind === "assistant_message"
                  ? html`<assistant-message .text=${entry.content}></assistant-message>`
                  : html`<details>
                      <summary>
                        ${icon("sparkles", 15)} ${researchStepCount(entry.calls.length)}
                      </summary>
                      ${toToolCallItems(entry).map(
                        (call) =>
                          html`<div class="tool">
                            <strong>${call.text}</strong>
                            <p>
                              ${call.status === "failed" ? msg("Fehlgeschlagen") : call.status === "completed" ? msg("Abgeschlossen") : msg("In Arbeit")}${call.retry ? ` · ${retryLabel(call.retry.attempt, call.retry.maxAttempts)}` : ""}
                            </p>
                            ${call.detail ? html`<p>${call.detail}</p>` : nothing}${call.resultItems?.map((item) => html`<p>${item.title}${item.artist ? ` · ${item.artist}` : ""}</p>`)}
                          </div>`,
                      )}
                    </details>`
            }
          </div>`,
      )}${this.pending ? this.pendingStatus() : nothing}<slot></slot>
    </div>`;
  }
}
