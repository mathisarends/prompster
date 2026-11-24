import { msg, localized } from "@lit/localize";
import { css, html, LitElement, nothing, type PropertyValues } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { pageStyles } from "@shared/styles/page";
import { emit } from "@shared/events";
import type { PendingInput } from "../state/chat-reducer";

@customElement("onboarding-panel")
@localized()
export class OnboardingPanel extends LitElement {
  @property({ attribute: false }) input: PendingInput | null = null;
  @property({ type: Boolean }) pending = false;
  @state() private selections: Record<string, string[]> = {};
  @state() private freeText: Record<string, string> = {};
  protected willUpdate(changed: PropertyValues): void {
    if (changed.has("input")) {
      for (const question of this.input?.questions ?? []) {
        if (!this.selections[question.id]) {
          this.selections[question.id] = question.answers;
        }
      }
    }
  }
  private submit(event: SubmitEvent): void {
    event.preventDefault();
    const questions = this.input?.questions ?? [];
    const answers = questions.map((question) => {
      const selected = [...(this.selections[question.id] ?? [])];
      const custom = this.freeText[question.id]?.trim();
      if (custom) {
        selected.push(custom);
      }
      return { questionId: question.id, answer: selected.join(", "), answers: selected };
    });
    if (answers.some((answer) => !answer.answers.length)) {
      return;
    }
    emit(this, "onboarding-submit", {
      answers,
      complete: questions.some((question) => question.isLastQuestion),
    });
  }
  static styles = css`
    ${pageStyles}
    :host {
      display: block;
      margin: 24px 0;
      padding: 20px;
      border: 1px solid var(--color-border);
      border-radius: var(--radius-card);
      background: var(--color-surface);
    }
    fieldset {
      margin: 0 0 24px;
      padding: 0;
      border: 0;
    }
    legend {
      margin-bottom: 4px;
      padding: 0;
      color: var(--color-text-strong);
      font-weight: var(--font-weight-medium);
    }
    .hint {
      margin: 0 0 4px;
      color: var(--color-muted);
      font-size: var(--font-size-label);
    }
    .options {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 12px;
    }
    label.option {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      height: 32px;
      padding: 0 14px 0 10px;
      border: 1px solid var(--color-border-strong);
      border-radius: var(--radius-pill);
      color: var(--color-text);
      font-size: var(--font-size-label);
      cursor: pointer;
      transition:
        background 0.12s,
        color 0.12s;
    }
    label.option:hover {
      background: var(--color-chip);
    }
    label.option:has(input:checked) {
      border-color: var(--color-text-strong);
      background: var(--color-text-strong);
      color: var(--color-inverse);
    }
    label.option input {
      width: 14px;
      height: 14px;
      margin: 0;
      accent-color: var(--color-inverse);
    }
    input[type="text"] {
      margin-top: 12px;
    }
  `;
  render() {
    if (!this.input) {
      return nothing;
    }
    const questions = this.input.questions;
    const ready =
      questions.length > 0 &&
      questions.every(
        (question) =>
          (this.selections[question.id]?.length ?? 0) > 0 || this.freeText[question.id]?.trim(),
      );
    return html`<form @submit=${this.submit}>
      ${questions.map(
        (question) =>
          html`<fieldset ?disabled=${this.pending}>
            <legend>${question.question}</legend>
            ${question.hint ? html`<p class="hint">${question.hint}</p>` : nothing}
            <div class="options">
              ${question.options.map(
                (option) =>
                  html`<label class="option"
                    ><input
                      type=${question.selectionMode === "multi_select" ? "checkbox" : "radio"}
                      name=${question.id}
                      .checked=${(this.selections[question.id] ?? []).includes(option)}
                      @change=${(event: Event) => {
                        const checked = (event.target as HTMLInputElement).checked;
                        this.selections = {
                          ...this.selections,
                          [question.id]:
                            question.selectionMode === "single_select"
                              ? [option]
                              : checked
                                ? [...(this.selections[question.id] ?? []), option]
                                : (this.selections[question.id] ?? []).filter(
                                    (value) => value !== option,
                                  ),
                        };
                        if (question.selectionMode === "single_select") {
                          this.freeText = { ...this.freeText, [question.id]: "" };
                        }
                      }}
                    />${option}</label
                  >`,
              )}
            </div>
            <input
              class="input"
              type="text"
              aria-label=${msg("Eigene Antwort")}
              placeholder=${msg("Oder deine eigene Antwort …")}
              maxlength="1000"
              .value=${this.freeText[question.id] ?? ""}
              @input=${(event: Event) => {
                this.freeText = {
                  ...this.freeText,
                  [question.id]: (event.target as HTMLInputElement).value,
                };
                if (question.selectionMode === "single_select") {
                  this.selections = { ...this.selections, [question.id]: [] };
                }
              }}
            />
          </fieldset>`,
      )}<button class="button primary" ?disabled=${this.pending || !ready}>
        ${this.pending ? msg("Wird übernommen …") : questions.some((question) => question.isLastQuestion) ? msg("Deck zusammenstellen") : msg("Antwort übernehmen")}
      </button>
    </form>`;
  }
}
