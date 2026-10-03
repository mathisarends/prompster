import { css, html, LitElement, nothing, type PropertyValues } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { pageStyles } from "@shared/styles/page";
import { emit } from "@shared/events";
import type { PendingInput } from "../state/chat-reducer";

@customElement("onboarding-panel")
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
    ${pageStyles} :host {
      display: block;
      border: 1px solid var(--color-border);
      border-radius: 16px;
      padding: 22px;
      margin: 24px 0;
    }
    fieldset {
      border: 0;
      padding: 0;
      margin: 0 0 20px;
    }
    legend {
      font-weight: 500;
      margin-bottom: 10px;
    }
    label.option {
      display: flex;
      align-items: center;
      gap: 9px;
      padding: 7px 0;
      font-size: 13px;
    }
    .hint {
      color: var(--color-muted);
      font-size: 12px;
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
            ${question.hint ? html`<p class="hint">${question.hint}</p>` : nothing}${question.options.map(
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
            )}<input
              class="input"
              type="text"
              aria-label="Eigene Antwort"
              placeholder="Oder deine eigene Antwort …"
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
        ${this.pending ? "Wird übernommen …" : questions.some((question) => question.isLastQuestion) ? "Deck zusammenstellen" : "Antwort übernehmen"}
      </button>
    </form>`;
  }
}
