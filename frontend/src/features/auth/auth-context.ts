import { createContext } from "react";

export type AuthStatus = "resolving" | "authenticated" | "unauthenticated";

export type AuthContextValue = {
  status: AuthStatus;
  isSignedIn: boolean;
  signIn: () => Promise<void>;
  signOut: () => Promise<void>;
};

export const AuthContext = createContext<AuthContextValue | null>(null);
