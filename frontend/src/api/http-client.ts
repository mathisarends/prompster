import Axios, { type AxiosError, type AxiosRequestConfig } from "axios";

type RetryableRequestConfig = AxiosRequestConfig & {
  _retry?: boolean;
  skipAuthRefresh?: boolean;
};

export const resolveApiBaseUrl = (): string => {
  const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL;
  if (configuredApiBaseUrl) {
    return configuredApiBaseUrl;
  }

  if (typeof window !== "undefined") {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }

  return "http://localhost:8000";
};

export const AXIOS_INSTANCE = Axios.create({
  baseURL: resolveApiBaseUrl(),
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

let refreshPromise: Promise<void> | null = null;

const isRefreshRequest = (config: RetryableRequestConfig): boolean => {
  const requestUrl = config.url ?? "";
  return (
    requestUrl.includes("/api/v1/auth/refresh") ||
    requestUrl.includes("/auth/refresh")
  );
};

AXIOS_INSTANCE.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as RetryableRequestConfig | undefined;

    if (
      error.response?.status !== 401 ||
      !originalRequest ||
      originalRequest.skipAuthRefresh ||
      originalRequest._retry ||
      isRefreshRequest(originalRequest)
    ) {
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    try {
      if (!refreshPromise) {
        refreshPromise = AXIOS_INSTANCE({
          url: "/api/v1/auth/refresh",
          method: "POST",
          skipAuthRefresh: true,
        } as RetryableRequestConfig)
          .then(() => undefined)
          .finally(() => {
            refreshPromise = null;
          });
      }

      await refreshPromise;
      return AXIOS_INSTANCE(originalRequest);
    } catch (refreshError) {
      return Promise.reject(refreshError);
    }
  },
);

export const customInstance = <T>(
  config: AxiosRequestConfig,
  options?: AxiosRequestConfig,
): Promise<T> => {
  const source = Axios.CancelToken.source();

  const promise = AXIOS_INSTANCE({
    ...config,
    ...options,
    cancelToken: source.token,
  }).then(({ data }) => data);

  // Keep cancel attached for react-query cancellation integration.
  // @ts-expect-error Orval expects this runtime property.
  promise.cancel = () => {
    source.cancel("Query was cancelled");
  };

  return promise;
};

export type ErrorType<Error> = AxiosError<Error>;
export type BodyType<BodyData> = BodyData;
