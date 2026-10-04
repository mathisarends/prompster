import { localized, msg } from "@lit/localize";
import { css, html, LitElement, nothing } from "lit";
import { customElement, property } from "lit/decorators.js";
import type { LLMOptionResponse } from "@api/generated/llm-options";
import { emit } from "@shared/events";
import { modelProvider, providerIcon } from "@shared/ui/chat/model-provider";

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
      max-width: 250px;
    }
    label {
      display: flex;
      align-items: center;
      gap: 6px;
      color: var(--color-muted);
      border-radius: 6px;
      padding-left: 6px;
    }
    label:focus-within {
      outline: 2px solid var(--color-accent);
      outline-offset: 2px;
    }
    .provider {
      display: flex;
      flex: 0 0 18px;
    }
    select {
      min-width: 0;
      max-width: 100%;
      min-height: 34px;
      padding: 5px 2px;
      border: 0;
      outline: none;
      background: transparent;
      color: inherit;
      font: inherit;
      font-size: 12px;
      text-overflow: ellipsis;
      cursor: pointer;
    }
    select:disabled {
      cursor: default;
      opacity: 0.6;
    }
    option {
      color: var(--color-text);
      background: var(--color-panel);
    }
  `;

  render() {
    const selected =
      this.options.find((model) => model.id === this.value) ??
      this.options.find((model) => model.isDefault) ??
      this.options[0];
    return html`<label>
      ${selected ? html`<span class="provider" role="img" aria-label=${modelProvider(selected.provider).label} title=${modelProvider(selected.provider).name}>${providerIcon(selected.provider, 18)}</span>` : nothing}
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
