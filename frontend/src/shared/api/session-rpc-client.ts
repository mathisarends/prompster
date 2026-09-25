import { SessionRpcClient } from "@/api/session-rpc";
import { resolveApiBaseUrl } from "@/shared/api/http-client";

const socketUrl = (sessionId: string): string => {
  const url = new URL(
    `/api/v1/sessions/${encodeURIComponent(sessionId)}/stream`,
    resolveApiBaseUrl(),
  );
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
};

/** Own one connection for the lifetime of a streamed operation. */
export const withSessionRpcClient = async <T>(
  sessionId: string,
  signal: AbortSignal | undefined,
  run: (client: SessionRpcClient) => Promise<T>,
): Promise<T> => {
  if (signal?.aborted) throw signal.reason;

  const client = await SessionRpcClient.connect({ url: socketUrl(sessionId) });
  const abort = () => {
    void client.close();
  };
  signal?.addEventListener("abort", abort, { once: true });
  try {
    if (signal?.aborted) throw signal.reason;
    return await run(client);
  } finally {
    signal?.removeEventListener("abort", abort);
    await client.close();
  }
};
