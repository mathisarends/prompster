import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ChevronDown } from "lucide-react";
import { toast } from "sonner";

import type { UserCurationEventResponse } from "@/api/generated/model";
import {
  getGetSessionQueryKey,
  getListSessionsQueryKey,
  restoreUserCurationEvent,
} from "@/api/generated/session-api";
import { Button } from "@/shared/ui/button";
import { TooltipProvider } from "@/shared/ui/tooltip";
import { useLocalStorage } from "@/shared/hooks/useLocalStorage";
import { cn } from "@/shared/lib/utils";

import { UserCurationEventChip } from "../user-curation-event-chip";
import { UserCurationFallbackIcon } from "../user-curation-event-meta";

type UserCurationEventContextProps = {
  sessionId: string;
  events: UserCurationEventResponse[];
  className?: string;
  activeTrackUri?: string | null;
  isPlaybackActive?: boolean;
  onToggleTrackPlayback?: (event: UserCurationEventResponse) => void;
};

const formatEventCount = (count: number) =>
  count === 1 ? "1 Änderung" : `${count} Änderungen`;

export const UserCurationEventContext = ({
  sessionId,
  events,
  className,
  activeTrackUri,
  isPlaybackActive = false,
  onToggleTrackPlayback,
}: UserCurationEventContextProps) => {
  const queryClient = useQueryClient();
  const [isExpanded, setIsExpanded] = useLocalStorage(
    "prompster.chat.user-curation-events-expanded",
    true,
  );
  const [restoringEventId, setRestoringEventId] = useState<string | null>(null);

  const restoreMutation = useMutation({
    mutationFn: (eventId: string) =>
      restoreUserCurationEvent(sessionId, eventId),
    onMutate: (eventId) => {
      setRestoringEventId(eventId);
    },
    onSuccess: async (updatedSession) => {
      queryClient.setQueryData(
        getGetSessionQueryKey(sessionId),
        updatedSession,
      );
      await queryClient.invalidateQueries({
        queryKey: getListSessionsQueryKey(),
      });
    },
    onError: () => {
      toast.error("Änderung konnte nicht rückgängig gemacht werden.");
    },
    onSettled: () => {
      setRestoringEventId(null);
    },
  });

  if (events.length === 0) return null;

  return (
    <div className={cn("mb-2 px-1", className)}>
      <div className="flex items-center justify-between gap-3 rounded-xl border border-white/[0.06] bg-white/[0.03] px-3 py-2 text-xs text-muted-foreground">
        <div className="flex min-w-0 items-center gap-2">
          <span className="inline-flex size-6 shrink-0 items-center justify-center rounded-md bg-primary/15 text-primary">
            <UserCurationFallbackIcon className="size-3.5" />
          </span>
          <div className="min-w-0">
            <p className="truncate font-semibold text-foreground">
              Deine Änderungen
            </p>
            <p className="truncate">
              KI bezieht {formatEventCount(events.length)} mit ein
            </p>
          </div>
        </div>

        <Button
          type="button"
          variant="ghost"
          size="icon-xs"
          aria-label={
            isExpanded
              ? "Playlist-Kontext einklappen"
              : "Playlist-Kontext ausklappen"
          }
          aria-expanded={isExpanded}
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-muted-foreground hover:bg-white/10 hover:text-foreground"
        >
          <ChevronDown
            className={cn(
              "size-3.5 transition-transform",
              isExpanded ? "rotate-180" : "",
            )}
          />
        </Button>
      </div>

      {isExpanded ? (
        <TooltipProvider delay={180}>
          <div className="mt-2 flex max-h-36 flex-wrap gap-2 overflow-y-auto pr-1">
            {events.map((event) => (
              <UserCurationEventChip
                key={event.id}
                event={event}
                isRestoring={
                  restoreMutation.isPending && restoringEventId === event.id
                }
                isDisabled={restoreMutation.isPending}
                isPlaying={Boolean(
                  isPlaybackActive &&
                  event.trackSpotifyUri &&
                  event.trackSpotifyUri === activeTrackUri,
                )}
                onRestore={() => {
                  if (restoreMutation.isPending) return;
                  restoreMutation.mutate(event.id);
                }}
                onTogglePlayback={onToggleTrackPlayback}
              />
            ))}
          </div>
        </TooltipProvider>
      ) : null}
    </div>
  );
};
