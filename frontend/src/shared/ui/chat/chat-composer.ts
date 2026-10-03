import { msg, localized } from "@lit/localize";
import { css, html, LitElement, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { live } from "lit/directives/live.js";
import { workspaceStyles } from "@shared/styles/workspace";
import { icon } from "@shared/ui/icons";
import { emit } from "@shared/events";
import type { VoiceInput } from "@shared/ui/voice-input/voice-input";
import "@shared/ui/voice-input/voice-input";
import { speechErrorMessage } from "@shared/ui/voice-input/speech-errors";

@customElement("chat-composer")
@localized()
export class ChatComposer extends LitElement {
  @property() value = "";
  @property() context = "";
  @property({ type: Boolean }) pending = false;
  @property({ type: Boolean }) stopping = false;
  @property({ type: Boolean }) hasAttachments = false;
  @state() private dictating = false;
  @state() private interim = "";
  @state() private voiceError = "";
  private submit(event?: Event): void {
    event?.preventDefault();
    if ((!this.value.trim() && !this.hasAttachments) || this.pending || this.dictating) {
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
  protected updated(): void {
    const input = this.renderRoot.querySelector("textarea");
    if (input) {
      input.style.height = "auto";
      input.style.height = `${Math.min(input.scrollHeight, 180)}px`;
    }
  }
  private acceptTranscript(event: CustomEvent<string>): void {
    this.value = [this.value.trimEnd(), event.detail].filter(Boolean).join(" ").slice(0, 10000);
    emit(this, "draft-change", this.value);
    void this.updateComplete.then(() => this.focusInput());
  }
  static styles = css`
    ${workspaceStyles}
    :host {
      display: block;
    }
    form {
      padding: 16px 14px 10px;
      border: 1px solid var(--color-border);
      border-radius: 20px;
      background: var(--color-composer);
      box-shadow: 0 4px 20px #0001;
    }
    form:focus-within {
      border-color: var(--color-border-strong);
    }
    textarea {
      display: block;
      resize: none;
      width: 100%;
      min-height: 48px;
      max-height: 180px;
      border: 0;
      outline: none !important;
      background: transparent;
      color: var(--color-text);
      padding: 0 4px;
      font-size: 14px;
      line-height: 1.6;
    }
    footer {
      display: flex;
      align-items: center;
      gap: 4px;
      margin-top: 8px;
    }
    .tools {
      flex: 1;
      min-width: 0;
    }
    .actions {
      display: flex;
      gap: 4px;
      margin-left: auto;
      align-items: center;
    }
    .dictating .tools {
      display: none;
    }
    .voice-error {
      margin: 8px 4px 0;
      color: var(--color-error);
      font-size: 12px;
      line-height: 1.5;
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
    return html`<form
      class=${this.dictating ? "dictating" : ""}
      @submit=${this.submit}
      aria-busy=${this.pending}
    >
      <slot name="attachments"></slot>
      <textarea
        aria-label=${msg("Nachricht")}
        placeholder=${msg("Ein Deck voller 90er-Hits, zu denen alle mitsingen …")}
        maxlength="10000"
        rows="2"
        .value=${live(this.dictating && this.interim ? [this.value.trimEnd(), this.interim].filter(Boolean).join(" ") : this.value)}
        ?disabled=${this.pending}
        ?readonly=${this.dictating}
        @input=${this.input}
        @keydown=${(event: KeyboardEvent) => {
          if (event.key === "Escape" && this.dictating) {
            event.preventDefault();
            this.renderRoot.querySelector<VoiceInput>("voice-input")?.cancel();
          }
          if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
            this.submit(event);
          }
        }}
      ></textarea>
      ${this.voiceError ? html`<p class="voice-error" role="alert">${speechErrorMessage(this.voiceError)}</p>` : nothing}
      <footer>
        <div class="tools">
          <slot name="tools"
            ><span class="type">${icon("music", 15)} ${msg("Musik-Kartendeck")}</span></slot
          >
        </div>
        <div class="actions">
          <voice-input
            .disabled=${this.pending}
            .context=${this.context}
            @dictation-preview=${(event: CustomEvent<string>) => (this.interim = event.detail)}
            @dictation-active=${(event: CustomEvent<boolean>) => (this.dictating = event.detail)}
            @dictation-error=${(event: CustomEvent<string>) => (this.voiceError = event.detail)}
            @transcript=${this.acceptTranscript}
          ></voice-input>
          ${this.dictating ? nothing : this.pending ? html`<button class="send" type="button" aria-label=${msg("Antwort stoppen")} ?disabled=${this.stopping} @click=${() => this.dispatchEvent(new CustomEvent("stop-request", { bubbles: true, composed: true }))}>${icon("close", 18)}</button>` : html`<button class="send" type="submit" title=${msg("Nachricht senden")} aria-label=${msg("Nachricht senden")} ?disabled=${!this.value.trim() && !this.hasAttachments}>${icon("arrowUp", 19)}</button>`}
        </div>
      </footer>
    </form>`;
  }
}
