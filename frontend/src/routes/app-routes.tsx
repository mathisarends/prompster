import {
  Navigate,
  Route,
  Routes,
  useLocation,
  useParams,
} from "react-router-dom";

import { ProtectedRoute } from "@/auth/protected-route";
import { useAuth } from "@/auth/use-auth";
import { AppLayout } from "@/layouts/app-layout";
import { HomePage } from "@/pages/home-page";
import { LandingPage } from "@/pages/landing-page";
import { ChatPage } from "@/pages/chat-page";

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
);
