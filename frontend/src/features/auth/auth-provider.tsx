import { useCallback, useMemo, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { logout } from "@/api/generated/auth-api";
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
    return { authenticated: false };
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
    await queryClient.invalidateQueries({ queryKey: AUTH_QUERY_KEY });
    const result = await queryClient.fetchQuery({
      queryKey: AUTH_QUERY_KEY,
      queryFn: resolveAuthSession,
      staleTime: 0,
    });
    if (result.authenticated) {
      navigate("/new", { replace: true });
      return;
    }

    throw new Error("Session could not be loaded after sign-in.");
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
