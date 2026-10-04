import { msg, localized } from "@lit/localize";
import { html, LitElement, type PropertyValues } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { icon } from "@shared/ui/icons";
import { emit } from "@shared/events";
import { speechLocale } from "@shared/i18n";
import { SpeechSession, speechConstructor, type SpeechState } from "./speech-session";
import { voiceInputStyles } from "./voice-input.styles";

@customElement("voice-input")
@localized()
export class VoiceInput extends LitElement {
  @property({ type: Boolean }) disabled = false;
  @property() context = "";
  @state() private speech: SpeechState = { phase: "idle", transcript: "", error: null };
  private readonly session = new SpeechSession(
    (state) => {
      this.speech = state;
      emit(this, "dictation-preview", state.transcript);
      emit(this, "dictation-active", state.phase !== "idle");
      emit(this, "dictation-error", state.error ?? "");
    },
    (text) => emit(this, "transcript", text),
  );
  static styles = voiceInputStyles;

  protected willUpdate(changed: PropertyValues<this>): void {
    if (changed.has("context") || (changed.has("disabled") && this.disabled)) {
      this.session.cancel();
    }
  }
  disconnectedCallback(): void {
    this.session.cancel();
    super.disconnectedCallback();
  }
  cancel(): void {
    this.session.cancel();
  }
  private start(): void {
    const Recognition = speechConstructor();
    if (Recognition && !this.disabled) {
      this.session.start(Recognition, speechLocale());
    }
  }
  render() {
    const active = this.speech.phase !== "idle";
    const supported = Boolean(speechConstructor());
    const label =
      this.speech.phase === "starting"
        ? msg("Mikrofon wird gestartet …")
        : this.speech.phase === "stopping"
          ? msg("Wird transkribiert …")
          : this.speech.phase === "review"
            ? msg("Text übernehmen?")
            : msg("Ich höre zu …");
    const startLabel = supported
      ? msg("Diktieren")
      : msg("Diktieren wird von diesem Browser nicht unterstützt");
    return html`<div class="controls ${active ? "capture" : ""}">
      ${
        active
          ? html`
              <span class="status" role="status">${label}</span>
              <div
                class="wave ${this.speech.phase === "listening" ? "listening" : ""}"
                aria-hidden="true"
              >
                ${Array.from({ length: 5 }, () => html`<span></span>`)}
              </div>
              <button
                class="icon-button"
                type="button"
                aria-label=${msg("Diktat verwerfen")}
                title=${`${msg("Diktat verwerfen")} · Esc`}
                aria-keyshortcuts="Escape"
                @click=${this.cancel}
              >
                ${icon("close", 18)}
              </button>
              <button
                class="icon-button accept"
                type="button"
                aria-label=${msg("Text übernehmen")}
                title=${msg("Text übernehmen")}
                ?disabled=${this.speech.phase === "starting" || this.speech.phase === "stopping"}
                @click=${() => this.session.accept()}
              >
                ${icon("check", 18)}
              </button>
            `
          : html`<button
              class="icon-button"
              type="button"
              aria-label=${startLabel}
              title=${startLabel}
              ?disabled=${this.disabled || !supported}
              @click=${this.start}
            >
              ${icon("microphone", 19)}
            </button>`
      }
    </div>`;
  }
}
