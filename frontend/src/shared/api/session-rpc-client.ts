import { endpoints, SessionRpcClient } from "@/api/session-rpc";
import { resolveApiBaseUrl } from "@/shared/api/http-client";

const socketUrl = (sessionId: string): URL => {
  const url = new URL(
    endpoints.session({ session_id: encodeURIComponent(sessionId) }).url,
  );
  const apiUrl = new URL(resolveApiBaseUrl());
  url.protocol = apiUrl.protocol === "https:" ? "wss:" : "ws:";
  url.host = apiUrl.host;
  url.port = apiUrl.port;
  return url;
};

/** Own one connection for the lifetime of a streamed operation. */
export const withSessionRpcClient = async <T>(
  sessionId: string,
  signal: AbortSignal | undefined,
  run: (client: SessionRpcClient) => Promise<T>,
): Promise<T> => {
  signal?.throwIfAborted();

  let client: SessionRpcClient | undefined;
  let socket: WebSocket | undefined;
  const abort = () => {
    // Closing also cancels a handshake that has not finished yet.
    socket?.close();
  };
  signal?.addEventListener("abort", abort, { once: true });
  try {
    client = await SessionRpcClient.connect({
      url: socketUrl(sessionId),
      notificationOverflow: "close",
      socketFactory: (url, protocols) => {
        signal?.throwIfAborted();
        socket = new WebSocket(url, protocols ? [...protocols] : undefined);
        return socket;
      },
    });
    signal?.throwIfAborted();
    const result = await run(client);
    signal?.throwIfAborted();
    return result;
  } catch (error) {
    signal?.throwIfAborted();
    throw error;
  } finally {
    signal?.removeEventListener("abort", abort);
    if (client) await client.close();
    else socket?.close();
  }
};
