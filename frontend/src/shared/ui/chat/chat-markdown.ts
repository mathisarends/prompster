import { css, html, LitElement } from "lit";
import { customElement, property } from "lit/decorators.js";
import { unsafeHTML } from "lit/directives/unsafe-html.js";
import { marked } from "marked";
import DOMPurify from "dompurify";
import { workspaceStyles } from "@shared/styles/workspace";

@customElement("chat-markdown")
export class ChatMarkdown extends LitElement {
  @property() text = "";
  static styles = css`
    ${workspaceStyles} :host {
      display: block;
      overflow-wrap: anywhere;
    }
    p {
      margin: 0 0 14px;
    }
    p:last-child {
      margin-bottom: 0;
    }
    ul,
    ol {
      padding-left: 24px;
    }
    h1,
    h2,
    h3 {
      font-size: 1.15em;
    }
    pre {
      overflow-x: auto;
      padding: 16px;
      background: var(--color-sidebar);
      border-radius: 12px;
    }
    code {
      font-family: var(--font-mono);
      font-size: 0.85em;
    }
    table {
      border-collapse: collapse;
      display: block;
      max-width: 100%;
      overflow-x: auto;
    }
    td,
    th {
      border: 1px solid var(--color-border);
      padding: 8px;
    }
    a {
      color: var(--color-accent);
    }
  `;
  render() {
    return html`${unsafeHTML(DOMPurify.sanitize(marked.parse(this.text, { async: false }), { USE_PROFILES: { html: true }, FORBID_TAGS: ["img", "video", "audio", "iframe"] }))}`;
  }
}
