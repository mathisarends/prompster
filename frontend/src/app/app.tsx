import { useAuth } from "@/features/auth";
import { AppRoutes } from "@/app/app-routes";

const AppShell = () => {
  const { status } = useAuth();

  if (status === "resolving") {
    return <div className="home-page-background min-h-dvh" aria-busy="true" />;
  }

  return <AppRoutes />;
};

export const App = () => <AppShell />;
