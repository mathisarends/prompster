import { createApiFetch, type ApiRequestOptions } from "lit-canon-fetch";

export { ApiError } from "lit-canon-fetch";
export type { ApiProblem, ApiRequestOptions } from "lit-canon-fetch";

export function resolveApiBaseUrl(): string {
  return (
    import.meta.env?.VITE_API_BASE_URL?.replace(/\/+$/, "") ||
    (typeof window !== "undefined" ? window.location.origin : "http://127.0.0.1:8000")
  );
}

const baseUrl = resolveApiBaseUrl();
let refreshPromise: Promise<void> | null = null;

const request = createApiFetch({
  baseUrl,
  middleware: [
    async (request, next) => {
      const response = await next(request);
      if (response.status !== 401 || request.url.startsWith(`${baseUrl}/api/v1/auth/`)) {
        return response;
      }

      await response.body?.cancel();
      await refreshAuthentication();
      request.init.signal?.throwIfAborted();
      return next(request);
    },
  ],
});

export function apiFetch<T>(url: string, options?: ApiRequestOptions): Promise<T> {
  return request<T>(url, options);
}

/** Renews the access cookie once, however many requests saw it expire. */
export function refreshAuthentication(): Promise<void> {
  refreshPromise ??= apiFetch<void>("/api/v1/auth/refresh", { method: "POST" }).finally(() => {
    refreshPromise = null;
  });
  return refreshPromise;
}
