import { Navigate, Outlet, Route, Routes, useNavigate } from "react-router-dom";
import { PanelLeft } from "lucide-react";
import { InteractiveDeckPage } from "./pages/InteractiveDeckPage";
import { HomePage } from "./pages/HomePage";
import { NavigationSidebar } from "@/components/navigation-sidebar";
import { useLocalStorage } from "@/hooks/useLocalStorage";
import { useViewport } from "@/hooks/useViewport";
import { type ChatHistoryEntry } from "@/lib/mockChats";
import { cn } from "@/lib/utils";

const AppLayout = () => {
  const navigate = useNavigate();
  const { isMobile } = useViewport();
  const [sidebarOpen, setSidebarOpen] = useLocalStorage(
    "prompster.sidebar.open",
    window.innerWidth >= 640,
  );
  const [activeChatId, setActiveChatId] = useLocalStorage<string | undefined>(
    "prompster.sidebar.active-chat",
    undefined,
  );

  const handleSelectChat = (chat: ChatHistoryEntry) => {
    setActiveChatId(chat.id);
    if (isMobile) setSidebarOpen(false);
    navigate("/deck/mock", { state: { prompt: chat.title } });
  };

  const handleNewChat = () => {
    setActiveChatId(undefined);
    if (isMobile) setSidebarOpen(false);
    navigate("/new", { state: { newChatAt: Date.now() } });
  };

  const handleNewChatNewTab = () => {
    window.open("/new", "_blank");
  };

  return (
    <div className="relative min-h-dvh">
      <NavigationSidebar
        open={sidebarOpen}
        onToggle={() => setSidebarOpen((prev) => !prev)}
        onNewChat={handleNewChat}
        onNewChatNewTab={handleNewChatNewTab}
        onSelectChat={handleSelectChat}
        activeChatId={activeChatId}
      />

      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 sm:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {!sidebarOpen && (
        <button
          type="button"
          className="fixed left-3 top-3 z-50 flex size-8 items-center justify-center rounded-md text-foreground hover:bg-accent sm:hidden"
          onClick={() => setSidebarOpen(true)}
          aria-label="Sidebar öffnen"
        >
          <PanelLeft className="size-4" />
        </button>
      )}

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
