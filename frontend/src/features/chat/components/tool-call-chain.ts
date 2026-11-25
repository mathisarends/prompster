import { msg, localized } from "@lit/localize";
import { css, html, LitElement, nothing } from "lit";
import { customElement, property } from "lit/decorators.js";
import { retryLabel } from "@shared/i18n/messages";
import { pageStyles } from "@shared/styles/page";
import { icon, type IconName } from "@shared/ui/icons";
import "@shared/ui/track-cover";
import type { ToolCallItem } from "../types";

const icons: Record<string, IconName> = {
  search_tracks: "search",
  search_playlists: "playlist",
  get_spotify_playlist_tracks: "playlist",
  add_deck_tracks: "plus",
  remove_deck_tracks: "trash",
  replace_deck_tracks: "swap",
  self_review: "check",
};

/**
 * The tools the agent called in one block of work, one line each. A call that
 * found something opens to list what it found.
 */
@customElement("tool-call-chain")
@localized()
export class ToolCallChain extends LitElement {
  /** What the block of calls is about, if the agent named it. */
  @property() label = "";
  @property({ attribute: false }) calls: ToolCallItem[] = [];
  static styles = css`
    ${pageStyles}
    :host {
      display: block;
      color: var(--color-muted);
      font-size: var(--font-size-label);
    }
    .label {
      margin: 0 0 2px;
      color: var(--color-faint);
      font-size: var(--font-size-caption);
    }
    ul {
      margin: 0;
      padding: 0;
      list-style: none;
    }
    .step,
    summary {
      display: flex;
      align-items: center;
      gap: 10px;
      min-height: 28px;
    }
    summary {
      width: fit-content;
      max-width: 100%;
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
    .mark {
      display: grid;
      place-items: center;
      width: 16px;
      flex-shrink: 0;
      color: var(--color-faint);
    }
    .text {
      min-width: 0;
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
    }
    .running .text {
      color: var(--color-text);
    }
    .failed .mark,
    .failed .text {
      color: var(--color-error);
    }
    .spinner {
      width: 11px;
      height: 11px;
      border: 1.5px solid var(--color-border-strong);
      border-top-color: var(--color-text);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    .count {
      flex-shrink: 0;
      padding: 0 6px;
      border-radius: var(--radius-pill);
      background: var(--color-chip);
      color: var(--color-muted);
      font-size: var(--font-size-micro);
      font-variant-numeric: tabular-nums;
      line-height: 18px;
    }
    .chevron {
      display: grid;
      flex-shrink: 0;
      color: var(--color-faint);
      transition: transform 0.15s ease;
    }
    details[open] .chevron {
      transform: rotate(90deg);
    }
    .note {
      flex-shrink: 0;
      color: var(--color-faint);
    }
    .found {
      margin: 2px 0 8px 7px;
      padding: 2px 0 2px 18px;
      border-left: 1px solid var(--color-border);
    }
    .found li {
      display: flex;
      align-items: center;
      gap: 10px;
      min-height: 36px;
      color: var(--color-text);
    }
    .found track-cover {
      width: 28px;
      flex-shrink: 0;
    }
    .found p {
      min-width: 0;
      margin: 0;
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
    }
    .found span {
      color: var(--color-faint);
    }
    .failure {
      margin: 0 0 6px 26px;
      color: var(--color-faint);
      font-size: var(--font-size-caption);
    }
    @keyframes spin {
      to {
        transform: rotate(360deg);
      }
    }
    @media (prefers-reduced-motion: reduce) {
      .spinner {
        animation: none;
      }
    }
  `;
  private line(call: ToolCallItem) {
    const running = call.status === "running" || call.status === "pending";
    return html`<span class="mark"
        >${
          running
            ? html`<i class="spinner"></i>`
            : icon(
                call.status === "failed" ? "close" : (icons[call.actionType ?? ""] ?? "disc"),
                14,
              )
        }</span
      ><span class="text" title=${call.text}>${call.text}</span>${
        call.retry
          ? html`<span class="note"
              >${retryLabel(call.retry.attempt, call.retry.maxAttempts)}</span
            >`
          : nothing
      }${
        call.status === "failed"
          ? html`<span class="note">${msg("Fehlgeschlagen")}</span>`
          : nothing
      }`;
  }
  render() {
    const named = this.label && !this.calls.some((call) => call.text === this.label);
    return html`${named ? html`<p class="label">${this.label}</p>` : nothing}
      <ul>
        ${this.calls.map((call) => {
          const found = call.resultItems ?? [];
          return html`<li class=${call.status ?? "completed"}>
            ${
              found.length
                ? html`<details>
                    <summary>
                      ${this.line(call)}<span class="count">${found.length}</span
                      ><span class="chevron">${icon("right", 14)}</span>
                    </summary>
                    <ul class="found">
                      ${found.map(
                        (item) =>
                          html`<li>
                            <track-cover .src=${item.coverUrl}></track-cover>
                            <p>
                              ${item.title}${item.artist ? html`<span> · ${item.artist}</span>` : nothing}
                            </p>
                          </li>`,
                      )}
                    </ul>
                  </details>`
                : html`<div class="step">${this.line(call)}</div>`
            }${
              call.status === "failed" && call.detail
                ? html`<p class="failure">${call.detail}</p>`
                : nothing
            }
          </li>`;
        })}
      </ul>`;
  }
}
