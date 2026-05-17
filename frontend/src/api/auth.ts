import { logout, refresh } from "@/api/generated/auth/auth";
import { getMe } from "@/api/generated/users/users";
import { AXIOS_INSTANCE } from "@/api/http-client";

const GOOGLE_LOGIN_PATH = "/api/v1/auth/google/login";

const resolveOAuthOrigin = (): string | null => {
  if (typeof window === "undefined") {
    return null;
  }

  if (import.meta.env.DEV) {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }

  return null;
};

export const getGoogleOAuthLoginUrl = (): string => {
  const oauthOrigin = resolveOAuthOrigin();
  if (oauthOrigin) {
    return new URL(GOOGLE_LOGIN_PATH, oauthOrigin).toString();
  }

  const baseUrl = AXIOS_INSTANCE.defaults.baseURL;

  if (!baseUrl) {
    return GOOGLE_LOGIN_PATH;
  }

  return new URL(GOOGLE_LOGIN_PATH, baseUrl).toString();
};

export const fetchCurrentUser = () => getMe();

export const refreshAuthSession = () => refresh();

export const logoutAuthSession = () => logout();
