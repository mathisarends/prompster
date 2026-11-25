import { msg, localized } from "@lit/localize";
import { css, html, LitElement, nothing } from "lit";
import { customElement, property } from "lit/decorators.js";
import { repeat } from "lit/directives/repeat.js";
import { pageStyles } from "@shared/styles/page";
import { icon } from "@shared/ui/icons";
import "@shared/ui/track-cover";
import type { StageSearch } from "./stage";

/**
 * The deck's search field as the agent uses it: its query being typed and the
 * hits it found, with the ones it took marked.
 *
 * Display only. The chat already announces each search, so hosts hide this
 * element from assistive technology.
 */
@customElement("agent-search")
@localized()
export class AgentSearch extends LitElement {
  @property({ attribute: false }) search: StageSearch | null = null;
  static styles = css`
    ${pageStyles}
    :host {
      display: block;
    }
    .field {
      display: flex;
      align-items: center;
      gap: 10px;
      height: 40px;
      margin: 0;
      padding: 0 14px 0 12px;
      border: 1px solid var(--color-border);
      border-radius: var(--radius-pill);
      background: var(--color-surface);
      color: var(--color-text);
      font-size: var(--font-size-body);
    }
    .field > svg {
      flex-shrink: 0;
      color: var(--color-faint);
    }
    .query {
      flex: 1;
      min-width: 0;
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
    }
    .caret {
      display: inline-block;
      width: 1px;
      height: 1.15em;
      margin-left: 1px;
      vertical-align: text-bottom;
      background: var(--color-accent);
      animation: blink 1s steps(1) infinite;
    }
    .typing .caret {
      animation: none;
    }
    .agent {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      flex-shrink: 0;
      color: var(--color-muted);
      font-size: var(--font-size-caption);
    }
    .agent svg {
      color: var(--color-accent);
    }
    .hits {
      display: flex;
      gap: 6px;
      height: 36px;
      margin-top: 8px;
      overflow: hidden;
      mask-image: linear-gradient(to right, #000 calc(100% - 32px), transparent);
    }
    .hit,
    .ghost {
      flex-shrink: 0;
      height: 36px;
      border-radius: var(--radius-control);
      background: var(--color-active);
    }
    .hit {
      display: flex;
      align-items: center;
      gap: 8px;
      max-width: 168px;
      padding: 0 10px 0 4px;
      border: 1px solid transparent;
      color: var(--color-muted);
      font-size: var(--font-size-label);
      animation: appear 0.22s ease-out both;
      transition:
        border-color 0.2s,
        color 0.2s,
        background 0.2s;
    }
    .hit track-cover {
      position: relative;
      width: 28px;
      flex-shrink: 0;
    }
    .hit span {
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
    }
    .hit.picked {
      border-color: color-mix(in srgb, var(--color-accent) 45%, transparent);
      background: color-mix(in srgb, var(--color-accent) 10%, transparent);
      color: var(--color-text-strong);
    }
    .hit .check {
      display: none;
      flex-shrink: 0;
      color: var(--color-accent);
    }
    .hit.picked .check {
      display: block;
    }
    .ghost {
      width: 132px;
      animation: pulse 1.1s ease-in-out infinite;
    }
    .ghost:nth-child(2) {
      width: 156px;
      animation-delay: 0.12s;
    }
    .ghost:nth-child(3) {
      width: 112px;
      animation-delay: 0.24s;
    }
    .none {
      align-self: center;
      padding-left: 4px;
      color: var(--color-faint);
      font-size: var(--font-size-label);
    }
    @keyframes blink {
      50% {
        opacity: 0;
      }
    }
    @keyframes appear {
      from {
        opacity: 0;
        transform: translateY(4px);
      }
    }
    @keyframes pulse {
      50% {
        opacity: 0.45;
      }
    }
  `;
  render() {
    const search = this.search;
    if (!search) {
      return nothing;
    }
    return html`<div class="field ${search.status}">
        ${icon("search", 16)}
        <span class="query">${search.query}<i class="caret"></i></span>
        <span class="agent">${icon("sparkles", 13)}${msg("Agent")}</span>
      </div>
      <div class="hits">
        ${
          search.status === "results"
            ? search.hits.length
              ? repeat(
                  search.hits,
                  (hit) => `${search.callId}:${hit.key}`,
                  (hit) =>
                    html`<div class="hit ${search.picked.includes(hit.key) ? "picked" : ""}">
                      <track-cover .src=${hit.coverUrl}></track-cover>
                      <span>${hit.title}</span>
                      <i class="check">${icon("check", 14)}</i>
                    </div>`,
                )
              : html`<span class="none">${msg("Keine Treffer")}</span>`
            : search.status === "searching"
              ? html`<i class="ghost"></i><i class="ghost"></i><i class="ghost"></i>`
              : nothing
        }
      </div>`;
  }
}
