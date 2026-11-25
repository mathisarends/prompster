import { msg, localized } from "@lit/localize";
import { css, html, LitElement, nothing } from "lit";
import { customElement, property } from "lit/decorators.js";
import { repeat } from "lit/directives/repeat.js";
import { pageStyles } from "@shared/styles/page";
import { icon } from "@shared/ui/icons";
import "@shared/ui/track-cover";
import type { StageSearch } from "./stage";

/**
 * The deck's search as the agent uses it: its query being typed into the
 * field, and the hits in a list that lies over the deck, with the ones the
 * agent took marked.
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
      position: relative;
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
    /* The hits float over the deck like a search menu, so the list never jumps. */
    .hits {
      position: absolute;
      top: calc(100% + 6px);
      right: 0;
      left: 0;
      padding: 4px;
      border: 1px solid var(--color-border-strong);
      border-radius: var(--radius-card);
      background: var(--color-raised);
      box-shadow: var(--shadow-panel);
      opacity: 0;
      transform: translateY(-4px);
      visibility: hidden;
      transition:
        opacity 0.16s ease,
        transform 0.16s ease,
        visibility 0s 0.16s;
    }
    .hits.open {
      opacity: 1;
      transform: none;
      visibility: visible;
      transition-delay: 0s;
    }
    .hit,
    .ghost {
      display: flex;
      align-items: center;
      gap: 12px;
      height: 48px;
      padding: 0 10px 0 6px;
      border-radius: var(--radius-sm);
    }
    .hit {
      transition: background 0.2s;
    }
    .hit track-cover {
      width: 36px;
      flex-shrink: 0;
    }
    .meta {
      flex: 1;
      min-width: 0;
      line-height: 1.3;
    }
    .meta strong,
    .meta small {
      display: block;
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
    }
    .meta strong {
      color: var(--color-text-strong);
      font-size: var(--font-size-body);
      font-weight: var(--font-weight-regular);
    }
    .meta small {
      color: var(--color-muted);
      font-size: var(--font-size-label);
    }
    .hit > svg {
      flex-shrink: 0;
      color: var(--color-faint);
    }
    .hit.picked {
      background: var(--color-active);
    }
    .hit.picked > svg {
      color: var(--color-play);
    }
    .ghost i {
      height: 10px;
      border-radius: var(--radius-pill);
      background: var(--color-control);
      animation: pulse 1.1s ease-in-out infinite;
    }
    .ghost i:first-child {
      width: 36px;
      height: 36px;
      border-radius: var(--radius-xs);
    }
    .ghost i:last-child {
      width: 42%;
    }
    .ghost:nth-child(2) i:last-child {
      width: 58%;
    }
    .ghost:nth-child(3) i:last-child {
      width: 34%;
    }
    .none {
      margin: 0;
      padding: 14px 10px;
      color: var(--color-muted);
      font-size: var(--font-size-label);
    }
    @keyframes blink {
      50% {
        opacity: 0;
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
    const searching = search.status === "searching";
    return html`<div class="field ${search.status}">
        ${icon("search", 16)}
        <span class="query">${search.query}<i class="caret"></i></span>
      </div>
      <div class="hits ${searching || search.status === "results" ? "open" : ""}">
        ${
          searching
            ? [0, 1, 2].map(() => html`<div class="ghost"><i></i><i></i></div>`)
            : search.hits.length || search.status !== "results"
              ? repeat(
                  search.hits,
                  (hit) => `${search.callId}:${hit.key}`,
                  (hit) => {
                    const picked = search.picked.includes(hit.key);
                    return html`<div class="hit ${picked ? "picked" : ""}">
                      <track-cover .src=${hit.coverUrl}></track-cover>
                      <span class="meta"
                        ><strong>${hit.title}</strong
                        >${hit.artist ? html`<small>${hit.artist}</small>` : nothing}</span
                      >${icon(picked ? "check" : "plus", 16)}
                    </div>`;
                  },
                )
              : html`<p class="none">${msg("Keine Treffer")}</p>`
        }
      </div>`;
  }
}
