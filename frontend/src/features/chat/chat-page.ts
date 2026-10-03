import { createQueryController } from "@tanstack/lit-query";
import { css, html, LitElement, nothing, type PropertyValues } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { listLlmOptionsQuery } from "@api/generated/llm-options";
import type { UserMeResponse } from "@api/generated/users";
import { pageStyles } from "@shared/styles/page";
import { icon } from "@shared/ui/icons";
import { emit } from "@shared/events";
import { ChatController } from "./chat-controller";
import type { ChatAttachment } from "./components/attachments/attachment-types";
import type { SubmitOnboardingAnswerRequest } from "@api/generated/sessions";
import "./chat-welcome";
import "./components/chat-message-list";
import "./components/onboarding-panel";
import "./components/chat-attachments";
import "@features/deck/deck-panel";
import "@chat";
import "@shared/ui/breadcrumb";

@customElement("chat-page")
export class ChatPage extends LitElement {
  @property() sessionId = "";
  @property({ attribute: false }) user!: UserMeResponse;
  @property({ type: Boolean }) sidebarOpen = true;
  @state() private draft = "";
  @state() private attachments: ChatAttachment[] = [];
  @state() private workspaceOpen = window.innerWidth > 1000;
  @state() private workspaceExpanded = false;
  private drafts = new Map<string, { text: string; attachments: ChatAttachment[] }>();
  private chat = new ChatController(this);
  private models = createQueryController(this, listLlmOptionsQuery());
  protected willUpdate(changed: PropertyValues): void {
    if (changed.has("sessionId") && this.sessionId !== this.chat.id) {
      this.drafts.set(this.chat.id, { text: this.draft, attachments: this.attachments });
      const draft = this.drafts.get(this.sessionId);
      this.draft = draft?.text ?? "";
      this.attachments = draft?.attachments ?? [];
      void this.chat.open(this.sessionId);
    }
  }
  private send = async (): Promise<void> => {
    const text = this.draft;
    const attachments = this.attachments;
    const sessionId = this.sessionId;
    const sent = await this.chat.send(text, attachments);
    if (sent && this.draft === text && (this.sessionId === sessionId || !sessionId)) {
      this.draft = "";
      this.attachments = [];
      this.drafts.delete("");
    }
  };
  private addFiles(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.attachments = [
      ...this.attachments,
      ...Array.from(input.files ?? []).map((file) => ({
        id: crypto.randomUUID(),
        kind: "image" as const,
        title: file.name,
        file,
      })),
    ].slice(0, 8);
    input.value = "";
  }
  private composer() {
    const options = this.models().data?.items ?? [];
    return html`<chat-composer
      .value=${this.draft}
      .context=${this.sessionId}
      ?hasAttachments=${this.attachments.length > 0}
      ?pending=${this.chat.busy}
      ?stopping=${this.chat.stopping}
      @draft-change=${(event: CustomEvent<string>) => (this.draft = event.detail)}
      @prompt-submit=${this.send}
      @stop-request=${() => this.chat.stop()}
    >
      <chat-attachments
        slot="attachments"
        .items=${this.attachments}
        ?disabled=${this.chat.busy}
        @attachment-remove=${(event: CustomEvent<string>) => (this.attachments = this.attachments.filter((item) => item.id !== event.detail))}
      ></chat-attachments>
      <div slot="tools" class="composer-tools">
        <button
          class="icon-button"
          title="Bilder hinzufügen"
          aria-label="Bilder hinzufügen"
          ?disabled=${this.chat.busy || this.attachments.length >= 8}
          @click=${() => this.renderRoot.querySelector<HTMLInputElement>("#images")?.click()}
        >
          ${icon("plus", 20)}
        </button>
        <select
          aria-label="KI-Modell"
          ?disabled=${this.chat.busy || !options.length}
          .value=${this.chat.modelId ?? options.find((model) => model.isDefault)?.id ?? options[0]?.id ?? ""}
          @change=${(event: Event) => (this.chat.modelId = (event.target as HTMLSelectElement).value)}
        >
          ${options.map((model) => html`<option value=${model.id}>${model.label}</option>`)}
        </select>
      </div>
    </chat-composer>`;
  }
  static styles = css`
    ${pageStyles}
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
      min-height: 0;
    }
    .layout {
      display: flex;
      min-height: 0;
      flex: 1;
    }
    .chat {
      display: flex;
      flex-direction: column;
      flex: 1;
      min-width: 0;
      min-height: 0;
    }
    .chat.expanded {
      display: none;
    }
    .toolbar {
      display: flex;
      align-items: center;
      padding: 0 20px;
      height: 58px;
      flex-shrink: 0;
      gap: 10px;
    }
    .toolbar app-breadcrumb {
      flex: 1;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-size: 12px;
    }
    .toolbar .button {
      font-size: 11px;
    }
    .composer-area {
      width: min(100%, 780px);
      margin: 0 auto;
      padding: 12px 24px 20px;
    }
    .composer-tools {
      display: flex;
      align-items: center;
      gap: 4px;
      min-width: 0;
    }
    select {
      max-width: 175px;
      min-height: 34px;
      padding: 5px 7px;
      border: 0;
      background: transparent;
      color: var(--color-muted);
      font-size: 12px;
    }
    option {
      color: var(--color-text);
      background: var(--color-panel);
    }
    .inline-error {
      margin: 10px 24px;
    }
    deck-panel {
      width: min(46%, 600px);
      min-width: 340px;
      border-left: 1px solid var(--color-border);
    }
    deck-panel.expanded {
      flex: 1;
      width: auto;
    }
    onboarding-panel {
      margin: 10px 0 20px;
    }
    @media (max-width: 1000px) {
      deck-panel {
        width: 100%;
        min-width: 0;
      }
      .chat.panel-open {
        display: none;
      }
      .toolbar {
        padding-inline: 18px;
      }
    }
    @media (max-width: 480px) {
      .composer-area {
        padding-inline: 14px;
      }
      select {
        max-width: 100px;
      }
    }
  `;
  render() {
    const state = this.chat.state;
    const hasConversation = !!this.chat.id || this.chat.busy;
    return html`<div class="layout">
        <section
          class="chat ${this.workspaceOpen && hasConversation ? `panel-open ${this.workspaceExpanded ? "expanded" : ""}` : ""}"
        >
          <header class="toolbar">
            ${!this.sidebarOpen ? html`<button class="icon-button" aria-label="Seitenleiste öffnen" @click=${() => emit(this, "open-sidebar")}>${icon("panelLeft", 18)}</button>` : nothing}
            <app-breadcrumb
              label="Seitennavigation"
              .items=${[{ label: "Deckstudio" }, { label: state.title || "Neues Deck" }]}
            ></app-breadcrumb>
            ${
              hasConversation
                ? html`<button
                    class="button deck-toggle"
                    aria-expanded=${this.workspaceOpen}
                    @click=${() => {
                      this.workspaceOpen = !this.workspaceOpen;
                      this.workspaceExpanded = false;
                    }}
                  >
                    ${icon("layers", 15)}
                    ${this.workspaceOpen ? "Deck schließen" : "Dein Deck"}${state.playlist ? ` · ${state.playlist.tracks.length}` : ""}
                  </button>`
                : nothing
            }
          </header>
          ${this.chat.loading ? html`<div class="status" role="status">Deck wird geladen …</div>` : !hasConversation ? html`<studio-page ?pending=${this.chat.busy} @draft-change=${(event: CustomEvent<string>) => (this.draft = event.detail)}>${this.composer()}</studio-page>` : html`<chat-message-list .entries=${state.entries} ?pending=${this.chat.busy}>${state.pendingInput ? html`<onboarding-panel .input=${state.pendingInput} ?pending=${this.chat.busy} @onboarding-submit=${(event: CustomEvent<{ answers: SubmitOnboardingAnswerRequest[]; complete: boolean }>) => this.chat.answer(event.detail.answers, event.detail.complete)}></onboarding-panel>` : nothing}</chat-message-list>`}
          ${
            this.chat.error
              ? html`<p class="error inline-error" role="alert">
                  ${this.chat.error}${
                    this.chat.loading || this.chat.busy
                      ? nothing
                      : html` <button
                          class="text-button"
                          @click=${() => {
                            this.chat.session = undefined;
                            void this.chat.open(this.sessionId);
                          }}
                        >
                          Erneut laden
                        </button>`
                  }
                </p>`
              : nothing
          }
          ${hasConversation && !this.chat.loading ? html`<div class="composer-area">${this.composer()}</div>` : nothing}
        </section>
        ${
          this.workspaceOpen && hasConversation
            ? html`<deck-panel
                class=${this.workspaceExpanded ? "expanded" : ""}
                .expanded=${this.workspaceExpanded}
                .sessionId=${this.chat.id}
                .playlist=${state.playlist}
                .user=${this.user}
                .curationEvents=${this.chat.session?.unconsumedUserCurationEvents ?? []}
                ?busy=${this.chat.busy}
                @deck-changed=${() => this.chat.refresh()}
                @toggle-expand=${() => (this.workspaceExpanded = !this.workspaceExpanded)}
                @close-panel=${async () => {
                  this.workspaceOpen = false;
                  this.workspaceExpanded = false;
                  await this.updateComplete;
                  this.renderRoot.querySelector<HTMLButtonElement>(".deck-toggle")?.focus();
                }}
              ></deck-panel>`
            : nothing
        }
      </div>
      <input
        id="images"
        type="file"
        accept="image/png,image/jpeg,image/webp,image/gif"
        multiple
        hidden
        @change=${this.addFiles}
      />`;
  }
}
