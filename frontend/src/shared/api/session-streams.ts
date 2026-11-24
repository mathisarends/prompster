import { createClient } from "@/api/session-streams";
import { refreshAuthentication, resolveApiBaseUrl } from "@api/request";

/** Retries a stream once with a renewed access cookie, like REST calls do. */
const fetchWithRefresh: typeof fetch = async (input, init) => {
  const response = await fetch(input, init);
  if (response.status !== 401) {
    return response;
  }
  await response.body?.cancel();
  await refreshAuthentication();
  init?.signal?.throwIfAborted();
  return fetch(input, init);
};

/** Session streams are plain HTTP requests answered with Server-Sent Events. */
export const sessionStreams = () =>
  createClient({
    baseUrl: resolveApiBaseUrl(),
    credentials: "include",
    fetch: fetchWithRefresh,
  }).sessionStreams;
