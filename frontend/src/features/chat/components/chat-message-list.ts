import { msg, localized } from "@lit/localize";
import { css, html, LitElement, nothing, type PropertyValues } from "lit";
import { customElement, property, query } from "lit/decorators.js";
import { repeat } from "lit/directives/repeat.js";
import { pageStyles } from "@shared/styles/page";
import { icon } from "@shared/ui/icons";
import { emit } from "@shared/events";
import "@chat";
import "./tool-call-chain";
import type { RunStatus } from "@/api/session-streams";
import type { ChatEntry } from "../state/chat-reducer";
import { toToolCallItems } from "../state/chat-reducer";
import { followProgress } from "../state/tool-call-progress";
import type { ToolCallProgress } from "../types";

@customElement("chat-message-list")
@localized()
export class ChatMessageList extends LitElement {
  @property({ attribute: false }) entries: ChatEntry[] = [];
  @property({ type: Boolean }) pending = false;
  /** How far the workspace has shown the agent's work; the list keeps to it. */
  @property({ attribute: false }) progress: ToolCallProgress | null = null;
  @property({ attribute: false }) runStatus: RunStatus = "running";
  @query(".scroll") private scroller!: HTMLElement;
  private stick = true;
  protected updated(changed: PropertyValues): void {
    if (
      this.stick &&
      (changed.has("entries") || changed.has("pending") || changed.has("progress"))
    ) {
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
        return html`<p class="pending working" role="status">
          ${icon("disc", 16)} ${msg("Prompster arbeitet an deinem Deck …")}
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
    /* The agent's calls keep one rhythm across their sequences, up to its answer. */
    .entry.work {
      margin-bottom: 0;
    }
    .entry.work + .entry:not(.work) {
      margin-top: 24px;
    }
    .entry.work + .pending {
      margin-top: 10px;
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
    .pending.working svg {
      color: var(--color-muted);
      animation: spin 2.4s linear infinite;
    }
    @keyframes glow {
      50% {
        opacity: 0.35;
      }
    }
    @keyframes spin {
      to {
        transform: rotate(360deg);
      }
    }
    @media (prefers-reduced-motion: reduce) {
      .pending svg {
        animation: none;
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
    const { entries, behind } = followProgress(this.entries, this.progress);
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
        entries,
        (entry) => entry.id,
        (entry) =>
          html`<div class=${entry.kind === "tool_call_group" ? "entry work" : "entry"}>
            ${
              entry.kind === "user_message"
                ? html`<div class="attachments">
                      ${(entry.imageAttachments ?? []).map((url) => (/^https?:/.test(url) || url.startsWith("/") ? html`<a href=${url} target="_blank" rel="noopener noreferrer"><img src=${url} alt=${msg("Angehängtes Bild")} loading="lazy" /></a>` : nothing))}${entry.attachments?.map((item) => html`<span class="attachment">${icon("music", 14)}${item.title}</span>`)}${entry.userCurationEvents?.map((event) => html`<span class="attachment">${event.eventType === "track_added" ? "+" : "−"} ${event.trackTitle}</span>`)}
                    </div>
                    <human-message .text=${entry.content}></human-message>`
                : entry.kind === "assistant_message"
                  ? html`<assistant-message .text=${entry.content}></assistant-message>`
                  : html`<tool-call-chain
                      .label=${entry.label ?? ""}
                      .calls=${toToolCallItems(entry)}
                    ></tool-call-chain>`
            }
          </div>`,
      )}${this.pending || behind ? this.pendingStatus() : nothing}<slot></slot>
    </div>`;
  }
}
