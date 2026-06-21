import { useEffect, useState } from "react";
import { X } from "lucide-react";

import type { UserCurationEventResponse } from "@/api/generated/model";
import { UserCurationEventChip } from "@/features/deck/components/user-curation/user-curation-event-chip";
import { cn } from "@/shared/lib/utils";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogTitle,
} from "@/shared/ui/dialog";
import { TooltipProvider } from "@/shared/ui/tooltip";

type UserChatMessageProps = {
  text: string;
  imageAttachments?: string[];
  userCurationEvents?: UserCurationEventResponse[];
  activeTrackUri?: string | null;
  isPlaybackActive?: boolean;
  className?: string;
  onToggleUserCurationTrackPlayback?: (
    event: UserCurationEventResponse,
  ) => void;
};

export const UserChatMessage = ({
  text,
  imageAttachments = [],
  userCurationEvents = [],
  activeTrackUri,
  isPlaybackActive = false,
  className,
  onToggleUserCurationTrackPlayback,
}: UserChatMessageProps) => {
  const hasText = text.trim().length > 0;

  return (
    <div
      className={cn(
        "ml-auto flex max-w-[82%] flex-col items-end gap-2",
        className,
      )}
    >
      {imageAttachments.length > 0 && (
        <UserMessageImageGrid imageAttachments={imageAttachments} />
      )}
      {userCurationEvents.length > 0 && (
        <UserMessageCurationEvents
          events={userCurationEvents}
          activeTrackUri={activeTrackUri}
          isPlaybackActive={isPlaybackActive}
          onToggleTrackPlayback={onToggleUserCurationTrackPlayback}
        />
      )}
      {hasText && (
        <div className="whitespace-pre-line rounded-2xl bg-white/10 px-4 py-3 text-sm leading-relaxed text-foreground sm:text-base">
          {text}
        </div>
      )}
    </div>
  );
};

type UserMessageCurationEventsProps = {
  events: UserCurationEventResponse[];
  activeTrackUri?: string | null;
  isPlaybackActive: boolean;
  onToggleTrackPlayback?: (event: UserCurationEventResponse) => void;
};

const UserMessageCurationEvents = ({
  events,
  activeTrackUri,
  isPlaybackActive,
  onToggleTrackPlayback,
}: UserMessageCurationEventsProps) => (
  <TooltipProvider delay={180}>
    <div className="flex max-w-full flex-wrap justify-end gap-2">
      {events.map((event) => (
        <UserCurationEventChip
          key={event.id}
          event={event}
          isPlaying={Boolean(
            isPlaybackActive &&
              event.trackSpotifyUri &&
              event.trackSpotifyUri === activeTrackUri,
          )}
          onTogglePlayback={onToggleTrackPlayback}
          className="basis-auto bg-white/[0.04] sm:max-w-[18rem]"
        />
      ))}
    </div>
  </TooltipProvider>
);

type UserMessageImageGridProps = {
  imageAttachments: string[];
};

const UserMessageImageGrid = ({
  imageAttachments,
}: UserMessageImageGridProps) => (
  <div className="flex max-w-full flex-wrap justify-end gap-2">
    {imageAttachments.map((url, index) => (
      <UserMessageImage key={`${url}:${index}`} url={url} />
    ))}
  </div>
);

type UserMessageImageProps = {
  url: string;
};

const UserMessageImage = ({ url }: UserMessageImageProps) => {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!url.startsWith("blob:")) return;

    return () => {
      URL.revokeObjectURL(url);
    };
  }, [url]);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="group relative block size-28 overflow-hidden rounded-2xl border border-white/[0.08] bg-white/[0.05] text-left shadow-sm shadow-black/20 outline-none transition hover:border-white/20 focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-default sm:size-32"
        aria-label="Bild anzeigen"
      >
        <img src={url} alt="" className="h-full w-full object-cover" loading="lazy" />
      </button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent
          backdropClassName="bg-black/74 backdrop-blur-[1px]"
          className="inset-0 left-0 top-0 flex h-dvh max-h-none w-screen max-w-none translate-x-0 flex-col rounded-none border-0 bg-transparent p-0 text-white shadow-none data-open:zoom-in-100 data-closed:zoom-out-100"
          onClick={() => setOpen(false)}
        >
          <div className="pointer-events-none fixed inset-x-0 top-0 z-10 flex h-16 items-center justify-end px-5">
            <DialogTitle className="sr-only">Bildvorschau</DialogTitle>
            <DialogClose
              className="pointer-events-auto grid size-10 place-items-center rounded-full text-white/85 outline-none transition hover:bg-white/10 hover:text-white focus-visible:ring-2 focus-visible:ring-white/70"
              aria-label="Vorschau schliessen"
            >
              <X className="size-5" />
            </DialogClose>
          </div>

          <div className="flex min-h-0 flex-1 items-center justify-center p-6 sm:p-10">
            <img
              src={url}
              alt=""
              className="max-h-[calc(100dvh-5rem)] max-w-[calc(100vw-3rem)] object-contain"
              onClick={(event) => event.stopPropagation()}
            />
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};
