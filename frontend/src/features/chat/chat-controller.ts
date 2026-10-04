import { msg } from "@lit/localize";
import type { ReactiveController, ReactiveControllerHost } from "lit";
import { queryClient } from "@api/query-client";
import {
  createSession,
  getSessionQuery,
  stopMessage,
  submitOnboardingAnswer,
  type SessionResponse,
  type SubmitOnboardingAnswerRequest,
} from "@api/generated/sessions";
import { uploadImageAttachment } from "@api/generated/image-attachments";
import { emit, errorMessage } from "@shared/events";
import { chatReducer, createInitialChatState, type ChatAction } from "./state/chat-reducer";
import { streamCompleteOnboarding, streamSendMessage } from "./api/session-stream";
import type { ChatAttachment } from "./components/attachments/attachment-types";

type Host = ReactiveControllerHost & HTMLElement;

/** Session orchestration is independent of templates. A revision owns every async result. */
export class ChatController implements ReactiveController {
  state = createInitialChatState();
  session?: SessionResponse;
  id = "";
  loading = false;
  busy = false;
  stopping = false;
  error = "";
  modelId?: string;
  private revision = 0;
  private abort?: AbortController;
  private stopTimer?: number;
  constructor(private host: Host) {
    host.addController(this);
  }
  hostDisconnected(): void {
    this.cancel();
  }
  private dispatch(action: ChatAction): void {
    this.state = chatReducer(this.state, action);
    this.host.requestUpdate();
  }
  private cancel(): void {
    this.revision++;
    this.abort?.abort();
    window.clearTimeout(this.stopTimer);
    this.busy = false;
    this.stopping = false;
  }
  async open(id: string): Promise<void> {
    if (id === this.id && (this.session || !id)) {
      return;
    }
    this.cancel();
    this.id = id;
    this.session = undefined;
    this.error = "";
    this.dispatch({ type: "session/reset" });
    if (!id) {
      this.loading = false;
      return;
    }
    const revision = this.revision;
    this.loading = true;
    this.host.requestUpdate();
    try {
      const session = await queryClient.fetchQuery({ ...getSessionQuery(id), staleTime: 0 });
      if (revision === this.revision) {
        this.accept(session);
      }
    } catch (error) {
      if (revision === this.revision) {
        this.error = errorMessage(error);
      }
    } finally {
      if (revision === this.revision) {
        this.loading = false;
        this.host.requestUpdate();
      }
    }
  }
  private accept(session: SessionResponse): void {
    this.session = session;
    this.dispatch({ type: "session/loaded", session });
    emit(this.host, "session-changed");
  }
  async refresh(): Promise<void> {
    const revision = this.revision;
    const id = this.id;
    if (!id) {
      return;
    }
    const session = await queryClient.fetchQuery({ ...getSessionQuery(id), staleTime: 0 });
    if (revision === this.revision) {
      this.accept(session);
    }
  }
  async send(text: string, attachments: ChatAttachment[]): Promise<boolean> {
    if (this.busy || this.loading || (!text.trim() && !attachments.length)) {
      return false;
    }
    return this.run(async (signal) => {
      if (!this.id) {
        const session = await createSession({ signal });
        signal.throwIfAborted();
        this.id = session.id;
        this.accept(session);
        emit(this.host, "session-created", session.id);
      }
      const images = await Promise.all(
        attachments
          .filter((item) => item.kind === "image")
          .map(async (item) => {
            if (item.storageKey) {
              return {
                id: item.id,
                storageKey: item.storageKey,
                contentType: item.contentType!,
                fileName: item.title,
                sizeBytes: item.sizeBytes!,
              };
            }
            if (!item.file) {
              throw new Error(
                msg("Die Bilddatei ist nicht mehr verfügbar. Bitte erneut hinzufügen."),
              );
            }
            const image = await uploadImageAttachment({ file: item.file }, { signal });
            return {
              id: image.id,
              storageKey: image.storageKey,
              contentType: image.contentType,
              fileName: image.fileName,
              sizeBytes: image.sizeBytes,
            };
          }),
      );
      signal.throwIfAborted();
      const references = attachments
        .filter((item) => item.kind === "spotify-playlist" || item.kind === "spotify-artist")
        .map((item) => ({
          kind: item.kind as "spotify-playlist" | "spotify-artist",
          externalId: item.spotifyId ?? item.id,
          spotifyId: item.spotifyId ?? item.id,
          title: item.title,
          subtitle: item.subtitle,
          imageUrl: item.imageUrl,
        }));
      const content = text.trim() || msg("Analysiere die angehängten Bilder.");
      this.dispatch({
        type: "stream/started",
        userMessageText: content,
        attachments,
        userCurationEvents: this.session?.unconsumedUserCurationEvents,
      });
      await streamSendMessage(
        this.id,
        { content, attachments: references, imageAttachments: images },
        {
          signal,
          modelId: this.modelId,
          onEvent: (event) => {
            if (!signal.aborted) {
              this.dispatch({ type: "stream/event", event });
            }
          },
        },
      );
    });
  }
  async answer(answers: SubmitOnboardingAnswerRequest[], complete: boolean): Promise<void> {
    if (this.busy || !this.id) {
      return;
    }
    await this.run(async (signal) => {
      for (const answer of answers) {
        await submitOnboardingAnswer(this.id, answer, { signal });
      }
      if (complete) {
        this.dispatch({ type: "stream/started" });
        await streamCompleteOnboarding(this.id, {
          signal,
          modelId: this.modelId,
          onEvent: (event) => {
            if (!signal.aborted) {
              this.dispatch({ type: "stream/event", event });
            }
          },
        });
      }
    });
  }
  private async run(operation: (signal: AbortSignal) => Promise<void>): Promise<boolean> {
    const revision = this.revision;
    const abort = new AbortController();
    this.abort = abort;
    this.busy = true;
    this.error = "";
    this.host.requestUpdate();
    let succeeded = false;
    try {
      await operation(abort.signal);
      abort.signal.throwIfAborted();
      succeeded = true;
      await this.refresh();
    } catch (error) {
      if (!abort.signal.aborted && revision === this.revision) {
        this.error = errorMessage(error);
      }
    } finally {
      if (revision === this.revision) {
        this.busy = false;
        this.stopping = false;
        window.clearTimeout(this.stopTimer);
        this.dispatch({ type: "stream/finished" });
        emit(this.host, "session-changed");
      }
    }
    return succeeded;
  }
  async stop(): Promise<void> {
    if (!this.busy || this.stopping) {
      return;
    }
    this.stopping = true;
    this.host.requestUpdate();
    const abort = this.abort;
    try {
      if (this.id && this.state.isStreaming) {
        await stopMessage(this.id);
      }
      this.stopTimer = window.setTimeout(() => abort?.abort(), 1500);
    } catch (error) {
      this.error = errorMessage(error);
      abort?.abort();
    }
    this.host.requestUpdate();
  }
}
