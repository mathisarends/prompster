import { Outlet, useNavigate } from "react-router-dom";
import { PanelLeft } from "lucide-react";

import type { SessionSummaryResponse } from "@/api/generated/model";
import { NavigationSidebar } from "@/components/sidebar/navigation-sidebar";
import { useLocalStorage } from "@/hooks/useLocalStorage";
import { useViewport } from "@/hooks/useViewport";
import { cn } from "@/lib/utils";

export const AppLayout = () => {
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

  const handleSelectChat = (session: SessionSummaryResponse) => {
    setActiveChatId(session.id);
    if (isMobile) setSidebarOpen(false);
    navigate(`/chat/${session.id}`);
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
