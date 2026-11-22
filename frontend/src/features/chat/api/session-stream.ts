import type { RpcStream, SendMessageParams, SessionRpcClient } from "@/api/session-rpc";
import { withSessionRpcClient } from "@/shared/api/session-rpc-client";

type StreamItem<T> = T extends RpcStream<infer Item> ? Item : never;
export type SessionStreamEvent = StreamItem<
  Awaited<ReturnType<SessionRpcClient["session"]["sendMessage"]>>
>;

export type SessionMessageAttachmentRequest = NonNullable<SendMessageParams["attachments"]>[number];
export type ImageAttachmentReferenceRequest = NonNullable<
  SendMessageParams["imageAttachments"]
>[number];
export type SendMessageRequest = Omit<SendMessageParams, "modelId">;

type StreamSessionOptions = {
  signal?: AbortSignal;
  onEvent?: (event: SessionStreamEvent) => void;
  modelId?: string;
};

export const streamSendMessage = (
  sessionId: string,
  body: SendMessageRequest,
  options: StreamSessionOptions,
): Promise<void> =>
  withSessionRpcClient(sessionId, options.signal, async (client) => {
    for await (const event of await client.session.sendMessage({
      ...body,
      modelId: options.modelId,
    })) {
      options.onEvent?.(event);
      if (event.type === "error") {
        throw new Error(event.message || event.code);
      }
    }
  });

export const streamCompleteOnboarding = (
  sessionId: string,
  options: StreamSessionOptions,
): Promise<void> =>
  withSessionRpcClient(sessionId, options.signal, async (client) => {
    for await (const event of await client.session.completeOnboarding({
      modelId: options.modelId,
    })) {
      options.onEvent?.(event);
      if (event.type === "error") {
        throw new Error(event.message || event.code);
      }
    }
  });
