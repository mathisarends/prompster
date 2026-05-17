import { AuthProvider } from "@/auth/auth-provider";
import { useAuth } from "@/auth/use-auth";
import { AppRoutes } from "@/routes/app-routes";

const AppShell = () => {
  const { status } = useAuth();

  if (status === "resolving") {
    return <div className="home-page-background min-h-dvh" aria-busy="true" />;
  }

  return <AppRoutes />;
};

export const App = () => (
  <AuthProvider>
    <AppShell />
  </AuthProvider>
);
