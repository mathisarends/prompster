import { useCallback, useMemo, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { logout, refresh } from "@/api/generated/auth-api";
import { getMe } from "@/api/generated/user-api";

import {
  AuthContext,
  type AuthContextValue,
  type AuthStatus,
} from "./auth-context";

const AUTH_QUERY_KEY = ["auth", "session"] as const;

type AuthSessionResult = { authenticated: boolean };

const resolveAuthSession = async (): Promise<AuthSessionResult> => {
  try {
    await getMe();
    return { authenticated: true };
  } catch {
    try {
      await refresh();
      await getMe();
      return { authenticated: true };
    } catch {
      return { authenticated: false };
    }
  }
};

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data, isPending } = useQuery({
    queryKey: AUTH_QUERY_KEY,
    queryFn: resolveAuthSession,
    retry: false,
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  });

  const status: AuthStatus = isPending
    ? "resolving"
    : data?.authenticated
      ? "authenticated"
      : "unauthenticated";

  const signIn = useCallback(async () => {
    const result = await queryClient.fetchQuery({
      queryKey: AUTH_QUERY_KEY,
      queryFn: resolveAuthSession,
    });
    if (result.authenticated) {
      navigate("/new", { replace: true });
    }
  }, [navigate, queryClient]);

  const signOut = useCallback(async () => {
    try {
      await logout();
    } finally {
      queryClient.setQueryData<AuthSessionResult>(AUTH_QUERY_KEY, {
        authenticated: false,
      });
      window.localStorage.removeItem("prompster.spotify.connected");
      navigate("/", { replace: true });
    }
  }, [navigate, queryClient]);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      isSignedIn: status === "authenticated",
      signIn,
      signOut,
    }),
    [status, signIn, signOut],
  );

  return <AuthContext value={value}>{children}</AuthContext>;
};
