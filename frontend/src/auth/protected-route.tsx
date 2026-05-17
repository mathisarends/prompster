import { Navigate, Outlet } from "react-router-dom";

import { useAuth } from "./use-auth";

export const ProtectedRoute = () => {
  const { isSignedIn } = useAuth();

  if (!isSignedIn) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
};
