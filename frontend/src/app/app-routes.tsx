import { lazy, Suspense } from "react";
import {
  Navigate,
  Route,
  Routes,
  useLocation,
  useParams,
} from "react-router-dom";

import { ProtectedRoute, useAuth } from "@/features/auth";
import { AppLayout } from "@/app/app-layout";

const HomePage = lazy(() =>
  import("@/pages/home-page").then((m) => ({ default: m.HomePage })),
);
const LandingPage = lazy(() =>
  import("@/pages/landing-page").then((m) => ({ default: m.LandingPage })),
);
const ChatPage = lazy(() =>
  import("@/pages/chat-page").then((m) => ({ default: m.ChatPage })),
);
const RouteFallback = () => (
  <div className="fixed top-0 left-0 right-0 h-0.5 bg-muted overflow-hidden">
    <div className="h-full bg-foreground/30 animate-[progress_1s_ease-in-out_infinite]" />
  </div>
);

const HomePageRoute = () => {
  const location = useLocation();
  const state = location.state as { newChatAt?: number } | null;
  const key = state?.newChatAt ? `new-${state.newChatAt}` : "home-default";

  return <HomePage key={key} />;
};

const ChatPageRoute = () => {
  const { chatId } = useParams();
  return <ChatPage key={chatId} />;
};

const LandingRoute = () => {
  const { isSignedIn } = useAuth();
  return isSignedIn ? <Navigate to="/new" replace /> : <LandingPage />;
};

const FallbackRoute = () => {
  const { isSignedIn } = useAuth();
  return <Navigate to={isSignedIn ? "/new" : "/"} replace />;
};

export const AppRoutes = () => (
  <Suspense fallback={<RouteFallback />}>
    <Routes>
      <Route path="/" element={<LandingRoute />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/new" element={<HomePageRoute />} />
          <Route path="/chat/:chatId" element={<ChatPageRoute />} />
        </Route>
      </Route>
      <Route path="*" element={<FallbackRoute />} />
    </Routes>
  </Suspense>
);
