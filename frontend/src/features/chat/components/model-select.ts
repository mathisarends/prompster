import { localized, msg } from "@lit/localize";
import { css, html, LitElement, nothing } from "lit";
import { customElement, property } from "lit/decorators.js";
import type { LLMOptionResponse } from "@api/generated/llm-options";
import { emit } from "@shared/events";
import { modelProvider, providerIcon } from "@shared/ui/chat/model-provider";

/** "GPT 6 Luna (OpenAI)" → "GPT 6 Luna": the provider is already shown as an icon. */
const modelName = (label: string) => label.replace(/\s*\([^)]*\)\s*$/, "");

/**
 * T3-style model chip ("◎ GPT 6 Luna Schnell"). A transparent native select sits on
 * top, so keyboard, screen reader and mobile pickers keep working unchanged.
 */
@customElement("model-select")
@localized()
export class ModelSelect extends LitElement {
  @property({ attribute: false }) options: LLMOptionResponse[] = [];
  @property() value = "";
  @property({ type: Boolean }) disabled = false;

  static styles = css`
    :host {
      display: block;
      min-width: 0;
    }
    label {
      position: relative;
      display: flex;
      align-items: center;
      gap: 7px;
      height: 32px;
      padding: 0 8px;
      border-radius: var(--radius-control);
      color: var(--color-muted);
      font-size: var(--font-size-body);
      white-space: nowrap;
    }
    label:hover {
      background: var(--color-chip);
    }
    label:focus-within {
      outline: 2px solid var(--color-border-strong);
      outline-offset: 0;
    }
    .provider {
      display: flex;
      color: var(--color-text);
    }
    .name {
      overflow: hidden;
      text-overflow: ellipsis;
      color: var(--color-text);
      font-weight: var(--font-weight-semibold);
    }
    .profile {
      color: var(--color-muted);
    }
    select {
      position: absolute;
      inset: 0;
      width: 100%;
      opacity: 0;
      cursor: pointer;
      font: inherit;
    }
    select:disabled {
      cursor: default;
    }
    label:has(select:disabled) {
      opacity: 0.6;
    }
    option {
      color: var(--color-text);
      background: var(--color-surface);
    }
  `;

  render() {
    const selected =
      this.options.find((model) => model.id === this.value) ??
      this.options.find((model) => model.isDefault) ??
      this.options[0];
    return html`<label title=${selected?.label ?? msg("KI-Modell")}>
      ${selected ? html`<span class="provider" role="img" aria-label=${modelProvider(selected.provider).label} title=${modelProvider(selected.provider).name}>${providerIcon(selected.provider, 15)}</span><span class="name">${modelName(selected.label)}</span>${selected.profile ? html`<span class="profile">${selected.profile}</span>` : nothing}` : html`<span>${msg("KI-Modell")}</span>`}
      <select
        aria-label=${msg("KI-Modell")}
        title=${selected?.label ?? msg("KI-Modell")}
        ?disabled=${this.disabled || !this.options.length}
        @change=${(event: Event) => emit(this, "model-change", (event.currentTarget as HTMLSelectElement).value)}
      >
        ${this.options.length ? this.options.map((model) => html`<option value=${model.id} .selected=${model.id === selected?.id}>${model.label}</option>`) : html`<option>${msg("KI-Modell")}</option>`}
      </select>
    </label>`;
  }
}
