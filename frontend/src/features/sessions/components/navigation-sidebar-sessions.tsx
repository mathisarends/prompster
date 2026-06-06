import type { SessionSummaryResponse } from "@/api/generated/model";
import { SidebarSessionItem } from "@/features/sessions/components/sidebar-session-item";
import { ScrollArea } from "@/shared/ui/scroll-area";

type NavigationSidebarSessionsProps = {
  open: boolean;
  isLoadingSessions: boolean;
  sessions: SessionSummaryResponse[];
  starredSessions: SessionSummaryResponse[];
  historySessions: SessionSummaryResponse[];
  activeChatId?: string;
  onSelectChat: (session: SessionSummaryResponse) => void;
  onToggleStar: (session: SessionSummaryResponse) => void;
  onRenameChat: (session: SessionSummaryResponse) => void;
  onDeleteChat: (session: SessionSummaryResponse) => void;
  isTogglingFor: (sessionId: string) => boolean;
};

export const NavigationSidebarSessions = ({
  open,
  isLoadingSessions,
  sessions,
  starredSessions,
  historySessions,
  activeChatId,
  onSelectChat,
  onToggleStar,
  onRenameChat,
  onDeleteChat,
  isTogglingFor,
}: NavigationSidebarSessionsProps) => {
  if (!open) {
    return <div className="flex-1" />;
  }

  return (
    <ScrollArea className="min-h-0 flex-1 px-2">
      <div className="pb-2 pt-1">
        {isLoadingSessions ? (
          <p className="px-2 py-3 text-xs text-muted-foreground">
            Lade Verlauf...
          </p>
        ) : sessions.length === 0 ? (
          <p className="px-2 py-3 text-xs text-muted-foreground">
            Noch keine Sessions vorhanden.
          </p>
        ) : (
          <>
            {starredSessions.length > 0 ? (
              <div>
                <p className="px-2 pb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground/80">
                  Markiert
                </p>
                <ul className="space-y-0.5 pb-3">
                  {starredSessions.map((session) => (
                    <SidebarSessionItem
                      key={session.id}
                      session={session}
                      isActive={session.id === activeChatId}
                      onSelect={() => onSelectChat(session)}
                      onToggleStar={() => onToggleStar(session)}
                      onRename={() => onRenameChat(session)}
                      onDelete={() => onDeleteChat(session)}
                      isTogglingStar={isTogglingFor(session.id)}
                    />
                  ))}
                </ul>
              </div>
            ) : null}

            <div>
              <p className="px-2 pb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground/80">
                Verlauf
              </p>
              {historySessions.length === 0 ? (
                <p className="px-2 py-3 text-xs text-muted-foreground">
                  Keine weiteren Sessions im Verlauf.
                </p>
              ) : (
                <ul className="space-y-0.5">
                  {historySessions.map((session) => (
                    <SidebarSessionItem
                      key={session.id}
                      session={session}
                      isActive={session.id === activeChatId}
                      onSelect={() => onSelectChat(session)}
                      onToggleStar={() => onToggleStar(session)}
                      onRename={() => onRenameChat(session)}
                      onDelete={() => onDeleteChat(session)}
                      isTogglingStar={isTogglingFor(session.id)}
                    />
                  ))}
                </ul>
              )}
            </div>
          </>
        )}
      </div>
    </ScrollArea>
  );
};
