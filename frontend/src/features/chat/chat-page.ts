import { msg, localized } from "@lit/localize";
import { createQueryController } from "@tanstack/lit-query";
import { css, html, LitElement, nothing, type PropertyValues } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { listLlmOptionsQuery } from "@api/generated/llm-options";
import type { UserMeResponse } from "@api/generated/users";
import { pageStyles } from "@shared/styles/page";
import { icon } from "@shared/ui/icons";
import { emit } from "@shared/events";
import { matchesShortcut, shortcutKeys, shortcutTitle } from "@shared/shortcuts";
import { ChatController } from "./chat-controller";
import type { ChatAttachment } from "./components/attachments/attachment-types";
import type { SubmitOnboardingAnswerRequest } from "@api/generated/sessions";
import "./chat-welcome";
import "./components/chat-message-list";
import "./components/onboarding-panel";
import "./components/chat-attachments";
import "./components/model-select";
import "@features/deck/deck-panel";
import "@chat";
import "@shared/ui/breadcrumb";

@customElement("chat-page")
@localized()
export class ChatPage extends LitElement {
  @property() sessionId = "";
  @property({ attribute: false }) user!: UserMeResponse;
  @property({ type: Boolean }) sidebarOpen = true;
  @property({ type: Boolean }) active = true;
  @state() private draft = "";
  @state() private attachments: ChatAttachment[] = [];
  @state() private workspaceOpen = window.innerWidth > 1000;
  @state() private workspaceExpanded = false;
  private drafts = new Map<string, { text: string; attachments: ChatAttachment[] }>();
  private chat = new ChatController(this);
  private models = createQueryController(this, listLlmOptionsQuery());
  connectedCallback(): void {
    super.connectedCallback();
    window.addEventListener("keydown", this.keydown);
  }
  disconnectedCallback(): void {
    window.removeEventListener("keydown", this.keydown);
    super.disconnectedCallback();
  }
  private keydown = (event: KeyboardEvent): void => {
    if (!this.active || (!this.chat.id && !this.chat.busy)) {
      return;
    }
    if (matchesShortcut(event, "deck")) {
      event.preventDefault();
      if (this.workspaceOpen) {
        void this.closeWorkspace();
      } else {
        void this.openWorkspace();
      }
    }
    if (this.workspaceOpen && matchesShortcut(event, "expandDeck")) {
      event.preventDefault();
      this.workspaceExpanded = !this.workspaceExpanded;
    }
  };
  private openWorkspace = async (): Promise<void> => {
    this.workspaceOpen = true;
    await this.updateComplete;
    const panel = this.renderRoot.querySelector<LitElement>("deck-panel");
    await panel?.updateComplete;
    panel?.shadowRoot
      ?.querySelector<HTMLButtonElement>('[role="tab"][aria-selected="true"]')
      ?.focus();
  };
  private closeWorkspace = async (): Promise<void> => {
    this.workspaceOpen = false;
    this.workspaceExpanded = false;
    await this.updateComplete;
    this.renderRoot.querySelector<HTMLButtonElement>(".deck-toggle")?.focus();
  };
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
      .inactive=${!this.active}
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
          title=${msg("Bilder hinzufügen")}
          aria-label=${msg("Bilder hinzufügen")}
          ?disabled=${this.chat.busy || this.attachments.length >= 8}
          @click=${() => this.renderRoot.querySelector<HTMLInputElement>("#images")?.click()}
        >
          ${icon("paperclip", 18)}
        </button>
        ${this.pauseButton()}
      </div>
      <model-select
        slot="model"
        .options=${options}
        .value=${this.chat.modelId ?? ""}
        ?disabled=${this.chat.busy || !options.length}
        @model-change=${(event: CustomEvent<string>) => {
          this.chat.modelId = event.detail;
          this.requestUpdate();
        }}
      ></model-select>
    </chat-composer>`;
  }
  private pauseButton() {
    const { isStreaming, runStatus } = this.chat.state;
    if (!this.chat.busy || !isStreaming) {
      return nothing;
    }
    const paused = runStatus === "paused";
    const label = paused ? msg("Fortsetzen") : msg("Nach diesem Schritt pausieren");
    return html`<button
      class="icon-button"
      title=${label}
      aria-label=${label}
      aria-pressed=${paused}
      ?disabled=${this.chat.stopping}
      @click=${() => this.chat.togglePause()}
    >
      ${icon(paused ? "play" : "pause", 18)}
    </button>`;
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
      padding: 0 12px 0 16px;
      height: var(--header-height);
      flex-shrink: 0;
      gap: 8px;
    }
    .toolbar app-breadcrumb {
      flex: 1;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .composer-area {
      width: min(100%, calc(var(--content-width) + 48px));
      margin: 0 auto;
      padding: 8px 24px 14px;
    }
    .inline-error {
      margin: 10px 24px;
    }
    deck-panel {
      width: min(44%, 560px);
      min-width: 380px;
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
            ${!this.sidebarOpen ? html`<button class="icon-button" aria-label=${msg("Seitenleiste öffnen")} title=${shortcutTitle(msg("Seitenleiste öffnen"), "sidebar")} aria-keyshortcuts=${shortcutKeys("sidebar")} @click=${() => emit(this, "open-sidebar")}>${icon("panelLeft", 18)}</button>` : nothing}
            <app-breadcrumb
              label=${msg("Seitennavigation")}
              .items=${[{ label: msg("Deckstudio") }, { label: state.title || msg("Neues Deck") }]}
            ></app-breadcrumb>
            ${
              hasConversation && !this.workspaceOpen
                ? html`<button
                    class="icon-button deck-toggle"
                    aria-label=${msg("Deck öffnen")}
                    title=${shortcutTitle(msg("Deck öffnen"), "deck")}
                    aria-keyshortcuts=${shortcutKeys("deck")}
                    aria-expanded="false"
                    @click=${this.openWorkspace}
                  >
                    ${icon("panelRight", 16)}
                  </button>`
                : nothing
            }
          </header>
          ${this.chat.loading ? html`<div class="status" role="status">${msg("Deck wird geladen …")}</div>` : !hasConversation ? html`<studio-page ?pending=${this.chat.busy} @draft-change=${(event: CustomEvent<string>) => (this.draft = event.detail)}>${this.composer()}</studio-page>` : html`<chat-message-list .entries=${state.entries} .runStatus=${state.runStatus} ?pending=${this.chat.busy}>${state.pendingInput ? html`<onboarding-panel .input=${state.pendingInput} ?pending=${this.chat.busy} @onboarding-submit=${(event: CustomEvent<{ answers: SubmitOnboardingAnswerRequest[]; complete: boolean }>) => this.chat.answer(event.detail.answers, event.detail.complete)}></onboarding-panel>` : nothing}</chat-message-list>`}
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
                          ${msg("Erneut laden")}
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
                @deck-changed=${() => {
                  void this.chat.refresh();
                  emit(this, "session-changed");
                }}
                @toggle-expand=${() => (this.workspaceExpanded = !this.workspaceExpanded)}
                @close-panel=${this.closeWorkspace}
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
