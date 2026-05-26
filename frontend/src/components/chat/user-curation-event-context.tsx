import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ChevronDown,
  Loader2,
  Music2,
  Pin,
  PinOff,
  Plus,
  Trash2,
  Undo2,
} from "lucide-react";
import { toast } from "sonner";

import {
  UserCurationEventTypeResponse,
  type UserCurationEventResponse,
} from "@/api/generated/model";
import {
  getGetSessionQueryKey,
  getListSessionsQueryKey,
  restoreUserCurationEvent,
} from "@/api/generated/session-api";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useLocalStorage } from "@/hooks/useLocalStorage";
import { cn } from "@/lib/utils";

type UserCurationEventContextProps = {
  sessionId: string;
  events: UserCurationEventResponse[];
  className?: string;
};

type UserCurationEventMeta = {
  label: string;
  restoreTooltip: string;
  Icon: typeof Music2;
  className: string;
};

const eventMeta: Record<
  UserCurationEventResponse["eventType"],
  UserCurationEventMeta
> = {
  [UserCurationEventTypeResponse.track_added]: {
    label: "Hinzugefuegt",
    restoreTooltip: "Aenderung rueckgaengig machen",
    Icon: Plus,
    className: "border-emerald-400/20 bg-emerald-400/10 text-emerald-200",
  },
  [UserCurationEventTypeResponse.track_removed]: {
    label: "Entfernt",
    restoreTooltip: "Track wiederherstellen",
    Icon: Trash2,
    className: "border-rose-400/20 bg-rose-400/10 text-rose-200",
  },
  [UserCurationEventTypeResponse.track_pinned]: {
    label: "Gepinnt",
    restoreTooltip: "Pin loesen",
    Icon: Pin,
    className: "border-amber-300/25 bg-amber-300/10 text-amber-100",
  },
  [UserCurationEventTypeResponse.track_unpinned]: {
    label: "Pin geloest",
    restoreTooltip: "Erneut pinnen",
    Icon: PinOff,
    className: "border-sky-300/20 bg-sky-300/10 text-sky-100",
  },
};

const formatEventCount = (count: number) =>
  count === 1 ? "1 Aenderung" : `${count} Aenderungen`;

export const UserCurationEventContext = ({
  sessionId,
  events,
  className,
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
      queryClient.setQueryData(getGetSessionQueryKey(sessionId), updatedSession);
      await queryClient.invalidateQueries({ queryKey: getListSessionsQueryKey() });
    },
    onError: () => {
      toast.error("Aenderung konnte nicht rueckgaengig gemacht werden.");
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
            <Music2 className="size-3.5" />
          </span>
          <div className="min-w-0">
            <p className="truncate font-semibold text-foreground">
              Playlist-Kontext
            </p>
            <p className="truncate">
              {formatEventCount(events.length)} fuer die naechste Antwort
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
                onRestore={() => {
                  if (restoreMutation.isPending) return;
                  restoreMutation.mutate(event.id);
                }}
              />
            ))}
          </div>
        </TooltipProvider>
      ) : null}
    </div>
  );
};

const UserCurationEventChip = ({
  event,
  isRestoring,
  isDisabled,
  onRestore,
}: {
  event: UserCurationEventResponse;
  isRestoring: boolean;
  isDisabled: boolean;
  onRestore: () => void;
}) => {
  const meta = eventMeta[event.eventType];
  const Icon = meta.Icon;

  return (
    <div className="group/event flex min-w-0 flex-1 basis-64 items-center gap-2.5 rounded-xl border border-white/[0.06] bg-card/55 py-1.5 pl-1.5 pr-3 shadow-sm shadow-black/20 backdrop-blur-sm sm:max-w-[17rem]">
      <div className="relative grid size-10 shrink-0 place-items-center overflow-hidden rounded-md bg-white/[0.06] text-muted-foreground ring-1 ring-white/[0.04]">
        {event.trackCoverUrl ? (
          <img
            src={event.trackCoverUrl}
            alt={event.trackTitle}
            className="h-full w-full object-cover"
            loading="lazy"
          />
        ) : (
          <Music2 className="size-5" />
        )}
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex min-w-0 items-center gap-1.5">
          <span
            className={cn(
              "inline-flex h-5 shrink-0 items-center gap-1 rounded-md border px-1.5 text-[11px] font-semibold leading-none",
              meta.className,
            )}
          >
            <Icon className="size-3" />
            {meta.label}
          </span>
          <p className="min-w-0 truncate text-[13px] font-semibold leading-tight text-foreground">
            {event.trackTitle}
          </p>
        </div>
        <p className="mt-0.5 truncate text-[11px] text-muted-foreground">
          {event.trackArtist}
        </p>
      </div>

      <Tooltip>
        <TooltipTrigger
          render={
            <Button
              type="button"
              variant="ghost"
              size="icon-xs"
              disabled={isDisabled}
              aria-label={meta.restoreTooltip}
              onClick={onRestore}
              className="shrink-0 opacity-0 pointer-events-none text-muted-foreground transition-opacity group-hover/event:opacity-100 group-hover/event:pointer-events-auto hover:bg-white/10 hover:text-foreground"
            >
              {isRestoring ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Undo2 className="size-3.5" />
              )}
            </Button>
          }
        />
        <TooltipContent side="top" sideOffset={6} showArrow={false}>
          {isRestoring ? "Wird rueckgaengig gemacht..." : meta.restoreTooltip}
        </TooltipContent>
      </Tooltip>
    </div>
  );
};
