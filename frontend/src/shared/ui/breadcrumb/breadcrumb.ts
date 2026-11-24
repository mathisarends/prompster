import { msg, localized } from "@lit/localize";
import { css, html, LitElement, nothing } from "lit";
import { customElement, property } from "lit/decorators.js";
import { workspaceStyles } from "@shared/styles/workspace";

export type BreadcrumbItem = { label: string; href?: string };

@customElement("app-breadcrumb")
@localized()
export class AppBreadcrumb extends LitElement {
  @property({ attribute: false }) items: BreadcrumbItem[] = [];
  @property() label = "";
  @property({ type: Boolean }) compact = true;

  static styles = css`
    ${workspaceStyles}
    :host {
      display: block;
      min-width: 0;
    }
    ol {
      display: flex;
      align-items: center;
      gap: 8px;
      min-width: 0;
      margin: 0;
      padding: 0;
      list-style: none;
      font-size: var(--font-size-label);
    }
    li {
      display: flex;
      align-items: center;
      gap: 8px;
      min-width: 0;
      color: var(--color-muted);
    }
    li:last-child {
      color: var(--color-text);
      font-weight: var(--font-weight-regular);
    }
    .separator {
      color: var(--color-muted);
      font-weight: var(--font-weight-regular);
    }
    .label {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    a {
      text-decoration: none;
    }
    a:hover {
      text-decoration: underline;
    }
    @media (max-width: 1050px) {
      .compact li:not(:last-child),
      .compact .separator {
        display: none;
      }
    }
  `;

  render() {
    return html`<nav aria-label=${this.label || msg("Seitennavigation")}>
      <ol class=${this.compact ? "compact" : ""}>
        ${this.items.map((item, index) => {
          const current = index === this.items.length - 1;
          return html`<li>
            ${index ? html`<span class="separator" aria-hidden="true">/</span>` : nothing}
            ${
              item.href && !current
                ? html`<a class="label" href=${item.href} title=${item.label}>${item.label}</a>`
                : html`<span
                    class="label"
                    title=${item.label}
                    aria-current=${current ? "page" : nothing}
                    >${item.label}</span
                  >`
            }
          </li>`;
        })}
      </ol>
    </nav>`;
  }
}
