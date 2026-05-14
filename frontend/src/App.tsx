import { Navigate, Outlet, Route, Routes, useNavigate } from "react-router-dom";
import { InteractiveDeckPage } from "./pages/InteractiveDeckPage";
import { HomePage } from "./pages/HomePage";
import { NavigationSidebar } from "@/components/navigation-sidebar";
import { useLocalStorage } from "@/hooks/useLocalStorage";
import { type ChatHistoryEntry } from "@/lib/mockChats";
import { cn } from "@/lib/utils";

const AppLayout = () => {
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useLocalStorage(
    "prompster.sidebar.open",
    true,
  );
  const [activeChatId, setActiveChatId] = useLocalStorage<string | undefined>(
    "prompster.sidebar.active-chat",
    undefined,
  );

  const handleSelectChat = (chat: ChatHistoryEntry) => {
    setActiveChatId(chat.id);
    navigate("/deck/mock", { state: { prompt: chat.title } });
  };

  const handleNewChat = () => {
    setActiveChatId(undefined);
    navigate("/new", { state: { newChatAt: Date.now() } });
  };

  return (
    <div className="relative min-h-screen">
      <NavigationSidebar
        open={sidebarOpen}
        onToggle={() => setSidebarOpen((prev) => !prev)}
        onNewChat={handleNewChat}
        onSelectChat={handleSelectChat}
        activeChatId={activeChatId}
      />

      <div
        className={cn(
          "transition-[padding] duration-300 ease-out",
          sidebarOpen ? "sm:pl-72" : "sm:pl-14",
        )}
      >
        <Outlet />
      </div>
    </div>
  );
};

export const App = () => {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/new" element={<HomePage />} />
        <Route path="/deck/mock" element={<InteractiveDeckPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/new" replace />} />
    </Routes>
  );
};
