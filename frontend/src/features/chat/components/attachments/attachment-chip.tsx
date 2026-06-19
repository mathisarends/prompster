import { useState } from "react";
import { Disc3, Image, ListMusic, Music, User, X } from "lucide-react";

import { Button } from "@/shared/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogTitle,
} from "@/shared/ui/dialog";
import { cn } from "@/shared/lib/utils";

import type { ChatAttachment, ChatAttachmentKind } from "./attachment-types";

type AttachmentChipProps = {
  attachment: ChatAttachment;
  onRemove?: (attachment: ChatAttachment) => void;
  className?: string;
};

const kindMeta: Record<
  ChatAttachmentKind,
  { label: string; icon: typeof Music; rounded: string }
> = {
  image: { label: "Bild", icon: Image, rounded: "rounded-md" },
  "spotify-track": { label: "Track", icon: Music, rounded: "rounded-md" },
  "spotify-playlist": {
    label: "Playlist",
    icon: ListMusic,
    rounded: "rounded-md",
  },
  "spotify-artist": { label: "Artist", icon: User, rounded: "rounded-full" },
};

export const AttachmentChip = ({
  attachment,
  onRemove,
  className,
}: AttachmentChipProps) => {
  const meta = kindMeta[attachment.kind];
  const Icon = meta.icon;

  if (attachment.kind === "image") {
    return (
      <ImageAttachmentChip
        attachment={attachment}
        onRemove={onRemove}
        className={className}
      />
    );
  }

  return (
    <div
      className={cn(
        "group/attachment relative flex w-56 items-center gap-2.5 rounded-xl border border-white/[0.06] bg-white/[0.04] py-1.5 pl-1.5 pr-2.5 shadow-sm shadow-black/20 backdrop-blur-sm",
        className,
      )}
    >
      <div
        className={cn(
          "relative grid size-10 shrink-0 place-items-center overflow-hidden bg-white/[0.06] text-muted-foreground ring-1 ring-white/[0.04]",
          meta.rounded,
        )}
      >
        {attachment.imageUrl ? (
          <img
            src={attachment.imageUrl}
            alt={attachment.title}
            className="h-full w-full object-cover"
            loading="lazy"
          />
        ) : (
          <Disc3 className="size-5" />
        )}
      </div>

      <div className="min-w-0 flex-1">
        <p className="truncate text-[13px] font-semibold leading-tight">
          {attachment.title}
        </p>
        <div className="mt-0.5 flex items-center gap-1 text-[11px] text-muted-foreground">
          <Icon className="size-3" />
          <span className="truncate">
            {attachment.subtitle
              ? `${meta.label} · ${attachment.subtitle}`
              : meta.label}
          </span>
        </div>
      </div>

      {onRemove && (
        <Button
          type="button"
          variant="ghost"
          size="icon-xs"
          aria-label={`${attachment.title} entfernen`}
          onClick={() => onRemove(attachment)}
          className="absolute -right-1.5 -top-1.5 size-5 rounded-full border border-white/10 bg-slate-900/90 text-muted-foreground opacity-0 shadow-sm transition-opacity hover:bg-slate-800 hover:text-foreground group-hover/attachment:opacity-100 focus-visible:opacity-100"
        >
          <X className="size-3" />
        </Button>
      )}
    </div>
  );
};

const ImageAttachmentChip = ({
  attachment,
  onRemove,
  className,
}: AttachmentChipProps) => {
  const [open, setOpen] = useState(false);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <div
        className={cn(
          "group/attachment relative size-28 shrink-0 sm:size-32",
          className,
        )}
      >
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="block h-full w-full overflow-hidden rounded-2xl border border-white/[0.08] bg-white/[0.05] text-left shadow-sm shadow-black/20 outline-none ring-offset-background transition hover:border-white/20 focus-visible:ring-2 focus-visible:ring-ring"
          aria-label="Bildvorschau oeffnen"
        >
          {attachment.imageUrl ? (
            <img
              src={attachment.imageUrl}
              alt=""
              className="h-full w-full object-cover"
              loading="lazy"
            />
          ) : (
            <span className="grid h-full w-full place-items-center text-muted-foreground">
              <Image className="size-7" />
            </span>
          )}
        </button>

        {onRemove && (
          <Button
            type="button"
            variant="ghost"
            size="icon-xs"
            aria-label="Bild entfernen"
            onClick={() => onRemove(attachment)}
            className="absolute -right-2 -top-2 size-7 rounded-full border border-white/15 bg-black/90 text-white shadow-sm transition-colors hover:bg-black hover:text-white"
          >
            <X className="size-4" />
          </Button>
        )}
      </div>

      <DialogContent
        backdropClassName="bg-black/74 backdrop-blur-[1px]"
        className="inset-0 left-0 top-0 flex h-dvh max-h-none w-screen max-w-none translate-x-0 flex-col rounded-none border-0 bg-transparent p-0 text-white shadow-none data-open:zoom-in-100 data-closed:zoom-out-100"
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
          {attachment.imageUrl ? (
            <img
              src={attachment.imageUrl}
              alt=""
              className="max-h-[calc(100dvh-5rem)] max-w-[calc(100vw-3rem)] object-contain"
            />
          ) : (
            <Image className="size-12 text-white/55" />
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};
