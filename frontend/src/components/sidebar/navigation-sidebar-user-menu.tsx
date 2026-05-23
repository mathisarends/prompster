import { ChevronsUpDown, LogOut, Music2 } from "lucide-react";

import type { UserMeResponse } from "@/api/generated/model";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

type NavigationSidebarUserMenuProps = {
  open: boolean;
  user: UserMeResponse | undefined;
  isSpotifyOAuthLoading: boolean;
  onSpotifyConnect: () => void;
  onSpotifyDisconnect: () => void;
  onSignOut: () => void;
};

const getInitials = (name: string | undefined) => {
  if (!name) {
    return "";
  }

  return name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
};

export const NavigationSidebarUserMenu = ({
  open,
  user,
  isSpotifyOAuthLoading,
  onSpotifyConnect,
  onSpotifyDisconnect,
  onSignOut,
}: NavigationSidebarUserMenuProps) => {
  const initials = getInitials(user?.name);

  return (
    <div className="border-t border-sidebar-border px-1 py-3">
      <DropdownMenu>
        {open ? (
          <DropdownMenuTrigger
            aria-label="Profilmenue oeffnen"
            className="flex h-12 w-full cursor-pointer items-center gap-2.5 rounded-md border border-transparent px-2 text-left transition-colors hover:border-sidebar-border/80 hover:bg-sidebar-accent focus-visible:ring-2 focus-visible:ring-sidebar-ring data-[state=open]:border-sidebar-border/80 data-[state=open]:bg-sidebar-accent"
          >
            <Avatar className="bg-sidebar-accent" size="default">
              <AvatarFallback className="bg-sidebar-accent text-xs font-semibold text-sidebar-accent-foreground">
                {initials}
              </AvatarFallback>
            </Avatar>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">
                {user?.name ?? "Konto"}
              </p>
            </div>
            <ChevronsUpDown className="size-4 shrink-0 text-sidebar-foreground/70" />
          </DropdownMenuTrigger>
        ) : (
          <div className="grid place-items-center">
            <DropdownMenuTrigger
              aria-label="Profilmenue oeffnen"
              className="grid size-9 cursor-pointer place-items-center rounded-md border border-transparent transition-colors hover:border-sidebar-border/80 hover:bg-sidebar-accent focus-visible:ring-2 focus-visible:ring-sidebar-ring data-[state=open]:border-sidebar-border/80 data-[state=open]:bg-sidebar-accent"
            >
              <Avatar className="bg-sidebar-accent" size="default">
                <AvatarFallback className="bg-sidebar-accent text-xs font-semibold text-sidebar-accent-foreground">
                  {initials}
                </AvatarFallback>
              </Avatar>
            </DropdownMenuTrigger>
          </div>
        )}
        <DropdownMenuContent
          align={open ? "start" : "center"}
          side="top"
          sideOffset={8}
        >
          {user?.spotifyConnected ? (
            <DropdownMenuItem onClick={onSpotifyDisconnect}>
              <Music2 />
              <span>Spotify trennen</span>
            </DropdownMenuItem>
          ) : (
            <DropdownMenuItem
              onClick={onSpotifyConnect}
              disabled={isSpotifyOAuthLoading}
            >
              <Music2 />
              <span>
                {isSpotifyOAuthLoading
                  ? "Spotify verbindet..."
                  : "Spotify verbinden"}
              </span>
            </DropdownMenuItem>
          )}
          <DropdownMenuItem onClick={onSignOut}>
            <LogOut />
            <span>Abmelden</span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
};
