import { css, html, LitElement } from "lit";
import { customElement, property } from "lit/decorators.js";
import { live } from "lit/directives/live.js";
import { workspaceStyles } from "@shared/styles/workspace";
import { icon } from "@shared/ui/icons";

@customElement("chat-composer")
export class ChatComposer extends LitElement {
  @property() value = "";
  @property({ type: Boolean }) pending = false;
  @property({ type: Boolean }) stopping = false;
  @property({ type: Boolean }) hasAttachments = false;
  private submit(event?: Event): void {
    event?.preventDefault();
    if ((!this.value.trim() && !this.hasAttachments) || this.pending) {
      return;
    }
    this.dispatchEvent(
      new CustomEvent<string>("prompt-submit", {
        detail: this.value.trim(),
        bubbles: true,
        composed: true,
      }),
    );
  }
  private input(event: Event): void {
    const input = event.currentTarget as HTMLTextAreaElement;
    this.value = input.value;
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 180)}px`;
    this.dispatchEvent(
      new CustomEvent<string>("draft-change", {
        detail: this.value,
        bubbles: true,
        composed: true,
      }),
    );
  }
  focusInput(): void {
    this.renderRoot.querySelector("textarea")?.focus();
  }
  static styles = css`
    ${workspaceStyles}
    :host {
      display: block;
    }
    form {
      padding: 20px;
      border: 1px solid var(--color-border);
      border-radius: var(--radius-panel);
      background: var(--color-composer);
      box-shadow: 0 8px 40px #0002;
    }
    form:focus-within {
      border-color: var(--color-border-strong);
    }
    textarea {
      display: block;
      resize: none;
      width: 100%;
      min-height: 65px;
      max-height: 180px;
      border: 0;
      outline: none !important;
      background: transparent;
      color: var(--color-text);
      font-size: 15px;
      line-height: 1.7;
    }
    footer {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 13px;
    }
    .type {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      color: var(--color-muted);
      font-size: 12px;
    }
    .send {
      display: grid;
      place-items: center;
      width: 36px;
      height: 36px;
      margin-left: auto;
      padding: 0;
      border: 0;
      border-radius: 50%;
      background: var(--color-accent);
      color: var(--color-on-accent);
    }
    .send:disabled {
      cursor: default;
      opacity: 0.4;
    }
  `;
  render() {
    return html`<form @submit=${this.submit} aria-busy=${this.pending}>
      <slot name="attachments"></slot>
      <textarea
        aria-label="Nachricht"
        placeholder="Ein Deck voller 90er-Hits, zu denen alle mitsingen …"
        maxlength="10000"
        rows="2"
        .value=${live(this.value)}
        ?disabled=${this.pending}
        @input=${this.input}
        @keydown=${(event: KeyboardEvent) => {
          if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
            this.submit(event);
          }
        }}
      ></textarea>
      <footer>
        <slot name="tools"><span class="type">${icon("music", 15)} Musik-Kartendeck</span></slot
        >${this.pending ? html`<button class="send" type="button" aria-label="Antwort stoppen" ?disabled=${this.stopping} @click=${() => this.dispatchEvent(new CustomEvent("stop-request", { bubbles: true, composed: true }))}>${icon("close", 18)}</button>` : html`<button class="send" type="submit" title="Nachricht senden" aria-label="Nachricht senden" ?disabled=${!this.value.trim() && !this.hasAttachments}>${icon("arrowUp", 19)}</button>`}
      </footer>
    </form>`;
  }
}
