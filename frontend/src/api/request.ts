/** RFC 9457 problem details returned by the backend. */
export interface ApiProblem {
  type: string;
  title: string;
  status: number;
  detail?: string | null;
  instance?: string | null;
  code?: string;
  [key: string]: unknown;
}

export class ApiError extends Error {
  readonly status: number;
  readonly problem: ApiProblem | null;

  constructor(status: number, problem: ApiProblem | null) {
    super(problem?.detail || problem?.title || `HTTP ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.problem = problem;
  }
}

export type ApiRequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  query?: object;
  skipAuthRefresh?: boolean;
};

export function resolveApiBaseUrl(): string {
  return (
    import.meta.env?.VITE_API_BASE_URL?.replace(/\/+$/, "") ||
    (typeof window !== "undefined" ? window.location.origin : "http://127.0.0.1:8000")
  );
}

let refreshPromise: Promise<void> | null = null;

function withQuery(url: string, query: object | undefined): string {
  if (!query) {
    return url;
  }

  const params = new URLSearchParams();
  for (const [key, rawValue] of Object.entries(query)) {
    const values = Array.isArray(rawValue) ? rawValue : [rawValue];
    for (const value of values) {
      if (value !== undefined) {
        params.append(key, value === null ? "null" : String(value));
      }
    }
  }

  return params.size ? `${url}${url.includes("?") ? "&" : "?"}${params}` : url;
}

function isJsonBody(body: unknown): boolean {
  if (body === null || Array.isArray(body)) {
    return true;
  }
  if (typeof body !== "object") {
    return false;
  }
  const prototype: unknown = Object.getPrototypeOf(body);
  return prototype === Object.prototype || prototype === null;
}

function isJson(contentType: string | null): boolean {
  const mediaType = contentType?.split(";", 1)[0].trim().toLowerCase();
  return mediaType === "application/json" || mediaType?.endsWith("+json") === true;
}

function toProblem(value: unknown): ApiProblem | null {
  if (value === null || typeof value !== "object") {
    return null;
  }

  const candidate = value as Record<string, unknown>;
  if (typeof candidate.type !== "string") {
    return null;
  }
  if (typeof candidate.title !== "string") {
    return null;
  }
  if (typeof candidate.status !== "number") {
    return null;
  }

  return candidate as ApiProblem;
}

export async function apiFetch<T>(url: string, options?: ApiRequestOptions): Promise<T> {
  const {
    body: requestBody,
    query,
    headers: inputHeaders,
    skipAuthRefresh,
    ...requestOptions
  } = options ?? {};
  const headers = new Headers(inputHeaders);
  const jsonBody = requestBody !== undefined && isJsonBody(requestBody);
  if (jsonBody && !headers.has("content-type")) {
    headers.set("content-type", "application/json");
  }

  const baseUrl = resolveApiBaseUrl();
  const response = await fetch(`${baseUrl}${withQuery(url, query)}`, {
    ...requestOptions,
    credentials: requestOptions.credentials ?? "include",
    headers,
    body: jsonBody ? JSON.stringify(requestBody) : (requestBody as BodyInit | null | undefined),
  });
  if (response.status === 401 && !skipAuthRefresh && !url.startsWith("/api/v1/auth/")) {
    await response.body?.cancel();
    refreshPromise ??= apiFetch<void>("/api/v1/auth/refresh", {
      method: "POST",
      skipAuthRefresh: true,
    }).finally(() => {
      refreshPromise = null;
    });
    await refreshPromise;
    requestOptions.signal?.throwIfAborted();
    return apiFetch<T>(url, { ...options, skipAuthRefresh: true });
  }
  if (response.ok && response.headers.get("content-type")?.split(";", 1)[0] === "application/pdf") {
    return (await response.blob()) as T;
  }
  const responseBody =
    response.status === 204 || response.status === 205 ? "" : await response.text();
  const json = isJson(response.headers.get("content-type"));

  if (!response.ok) {
    let problem: ApiProblem | null = null;
    if (json && responseBody) {
      try {
        problem = toProblem(JSON.parse(responseBody));
      } catch {
        // An invalid error body must still surface as an HTTP error.
      }
    }
    throw new ApiError(response.status, problem);
  }

  if (!responseBody) {
    return undefined as T;
  }
  return (json ? JSON.parse(responseBody) : responseBody) as T;
}
