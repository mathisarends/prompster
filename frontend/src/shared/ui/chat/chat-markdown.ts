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
      color: var(--color-reading);
      font-size: var(--font-size-chat);
      line-height: 1.7;
      letter-spacing: -0.003em;
    }
    :first-child {
      margin-top: 0;
    }
    p {
      margin: 0 0 0.9em;
    }
    :last-child {
      margin-bottom: 0;
    }
    strong,
    b {
      color: var(--color-text-strong);
      font-weight: var(--font-weight-semibold);
    }
    ul,
    ol {
      margin: 0.4em 0 1em;
      padding-left: 1.3em;
    }
    li {
      margin: 0.25em 0;
      padding-left: 0.2em;
    }
    li::marker {
      color: var(--color-faint);
    }
    h1,
    h2,
    h3,
    h4 {
      margin: 1.5em 0 0.5em;
      color: var(--color-text-strong);
      font-weight: var(--font-weight-semibold);
      line-height: 1.35;
      letter-spacing: -0.015em;
    }
    h1 {
      font-size: 1.35em;
    }
    h2 {
      font-size: 1.2em;
    }
    h3,
    h4 {
      font-size: 1.05em;
    }
    blockquote {
      margin: 1em 0;
      padding-left: 1em;
      border-left: 2px solid var(--color-border-strong);
      color: var(--color-muted);
    }
    hr {
      margin: 1.5em 0;
      border: 0;
      border-top: 1px solid var(--color-border);
    }
    code {
      padding: 0.15em 0.4em;
      border-radius: var(--radius-xs);
      background: var(--color-raised);
      font-family: var(--font-mono);
      font-size: 0.86em;
    }
    pre {
      overflow-x: auto;
      margin: 1em 0;
      padding: 14px 16px;
      border: 1px solid var(--color-border);
      border-radius: var(--radius-control);
      background: var(--color-surface);
      line-height: 1.55;
    }
    pre code {
      padding: 0;
      background: none;
    }
    table {
      display: block;
      max-width: 100%;
      overflow-x: auto;
      margin: 1em 0;
      border-collapse: collapse;
      font-size: 0.93em;
    }
    th {
      color: var(--color-text-strong);
      font-weight: var(--font-weight-semibold);
      text-align: left;
    }
    td,
    th {
      padding: 8px 12px;
      border-bottom: 1px solid var(--color-border);
    }
    a {
      color: var(--color-text-strong);
      text-decoration: underline;
      text-decoration-color: var(--color-faint);
      text-underline-offset: 3px;
    }
    a:hover {
      text-decoration-color: currentColor;
    }
  `;
  render() {
    return html`${unsafeHTML(DOMPurify.sanitize(marked.parse(this.text, { async: false }), { USE_PROFILES: { html: true }, FORBID_TAGS: ["img", "video", "audio", "iframe"] }))}`;
  }
}
