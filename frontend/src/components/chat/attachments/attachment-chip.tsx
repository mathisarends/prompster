import { Disc3, ListMusic, Music, User, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

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
