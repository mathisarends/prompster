import type { SendMessageRequest, SessionStreamEvent } from "@/api/session-streams";
import { sessionStreams } from "@/shared/api/session-streams";

export type { SessionStreamEvent };
export type SendMessageBody = Omit<SendMessageRequest, "modelId">;

type StreamSessionOptions = {
  signal?: AbortSignal;
  onEvent?: (event: SessionStreamEvent) => void;
  modelId?: string;
};

const consume = async (
  events: AsyncIterable<SessionStreamEvent>,
  onEvent: StreamSessionOptions["onEvent"],
): Promise<void> => {
  for await (const event of events) {
    onEvent?.(event);
    if (event.type === "error") {
      throw new Error(event.message || event.code);
    }
  }
};

export const streamSendMessage = (
  sessionId: string,
  body: SendMessageBody,
  { signal, onEvent, modelId }: StreamSessionOptions,
): Promise<void> =>
  consume(
    sessionStreams().sendMessage({ sessionId, body: { ...body, modelId } }, { signal }),
    onEvent,
  );

export const streamCompleteOnboarding = (
  sessionId: string,
  { signal, onEvent, modelId }: StreamSessionOptions,
): Promise<void> =>
  consume(
    sessionStreams().completeOnboarding({ sessionId, body: { modelId } }, { signal }),
    onEvent,
  );
