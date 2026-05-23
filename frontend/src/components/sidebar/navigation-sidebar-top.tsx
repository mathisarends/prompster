import type { MouseEvent } from "react";
import { PanelLeft, Plus, Search } from "lucide-react";

import {
  KeyboardShortcutHint,
  type ShortcutKey,
} from "@/components/shared/keyboard-shortcut-hint";
import { SidebarInlineShortcutKeys } from "@/components/sidebar/sidebar-inline-shortcut-keys";
import { PrompsterLogo } from "@/components/prompster-logo";
import { Button } from "@/components/ui/button";

type NavigationSidebarTopProps = {
  open: boolean;
  onToggle: () => void;
  onNewChat: () => void;
  onNewChatNewTab?: () => void;
  onOpenSearch: () => void;
  newChatShortcut: ShortcutKey[];
  searchShortcut: ShortcutKey[];
  toggleSidebarShortcut: ShortcutKey[];
};

export const NavigationSidebarTop = ({
  open,
  onToggle,
  onNewChat,
  onNewChatNewTab,
  onOpenSearch,
  newChatShortcut,
  searchShortcut,
  toggleSidebarShortcut,
}: NavigationSidebarTopProps) => {
  const handleNewChatClick = (event: MouseEvent<HTMLButtonElement>) => {
    if ((event.ctrlKey || event.metaKey) && onNewChatNewTab) {
      event.preventDefault();
      onNewChatNewTab();
      return;
    }

    onNewChat();
  };

  if (open) {
    return (
      <div className="space-y-4 px-3 py-3">
        <div className="flex items-center justify-between gap-2">
          <PrompsterLogo />
          <KeyboardShortcutHint
            label="Sidebar einklappen"
            keys={toggleSidebarShortcut}
          >
            <Button
              size="icon-sm"
              variant="ghost"
              onClick={onToggle}
              aria-label="Sidebar einklappen"
              className="hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
            >
              <PanelLeft className="size-4 transition-transform" />
            </Button>
          </KeyboardShortcutHint>
        </div>

        <div className="space-y-1">
          <button
            type="button"
            onClick={handleNewChatClick}
            className="group flex h-10 w-full items-center gap-3 rounded-md px-2 text-left text-sm font-medium text-sidebar-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
          >
            <Plus className="size-5 shrink-0" />
            <span>Neuer Chat</span>
            <SidebarInlineShortcutKeys keys={newChatShortcut} />
          </button>
          <button
            type="button"
            onClick={onOpenSearch}
            className="group flex h-10 w-full items-center gap-3 rounded-md px-2 text-left text-sm font-medium text-sidebar-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
          >
            <Search className="size-5 shrink-0" />
            <span>Suchen</span>
            <SidebarInlineShortcutKeys keys={searchShortcut} />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-3 px-1 py-3">
      <KeyboardShortcutHint
        label="Sidebar ausklappen"
        keys={toggleSidebarShortcut}
      >
        <Button
          size="icon-sm"
          variant="ghost"
          onClick={onToggle}
          aria-label="Sidebar ausklappen"
          className="hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
        >
          <PanelLeft className="size-4 rotate-180 transition-transform" />
        </Button>
      </KeyboardShortcutHint>
      <KeyboardShortcutHint label="Neuer Chat" keys={newChatShortcut}>
        <Button
          size="icon-sm"
          variant="ghost"
          onClick={handleNewChatClick}
          aria-label="Neuen Chat starten"
          className="rounded-full bg-sidebar-accent hover:bg-sidebar-accent/80 hover:text-sidebar-accent-foreground"
        >
          <Plus className="size-4" />
        </Button>
      </KeyboardShortcutHint>
      <KeyboardShortcutHint label="Suchen" keys={searchShortcut}>
        <Button
          size="icon-sm"
          variant="ghost"
          onClick={onOpenSearch}
          aria-label="Suche oeffnen"
          className="hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
        >
          <Search className="size-5" />
        </Button>
      </KeyboardShortcutHint>
    </div>
  );
};
