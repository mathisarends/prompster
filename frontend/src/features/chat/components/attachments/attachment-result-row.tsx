import { forwardRef } from "react";
import { Music, Plus } from "lucide-react";

import { cn } from "@/shared/lib/utils";

import type { ChatAttachment } from "./attachment-types";

type AttachmentResultRowProps = {
  attachment: ChatAttachment;
  isAttached: boolean;
  onPick: () => void;
  isHighlighted?: boolean;
  onMouseEnter?: () => void;
};

export const AttachmentResultRow = forwardRef<
  HTMLButtonElement,
  AttachmentResultRowProps
>(function AttachmentResultRow(
  { attachment, isAttached, onPick, isHighlighted = false, onMouseEnter },
  ref,
) {
  return (
    <button
      ref={ref}
      type="button"
      onClick={onPick}
      onMouseEnter={onMouseEnter}
      disabled={isAttached}
      className={cn(
        "group/row flex w-full items-center gap-2.5 rounded-md px-2 py-1.5 text-left transition-colors hover:bg-white/[0.05] disabled:cursor-not-allowed disabled:opacity-50",
        isHighlighted && "bg-white/[0.08]",
      )}
    >
      <div
        className={cn(
          "grid size-9 shrink-0 place-items-center overflow-hidden bg-white/[0.06] text-muted-foreground ring-1 ring-white/[0.04]",
          attachment.kind === "spotify-artist"
            ? "rounded-full"
            : "rounded-[4px]",
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
          <Music className="size-4" />
        )}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-[13px] font-medium leading-tight">
          {attachment.title}
        </p>
        {attachment.subtitle && (
          <p className="mt-0.5 truncate text-[11px] text-muted-foreground">
            {attachment.subtitle}
          </p>
        )}
      </div>
      <Plus
        className={cn(
          "size-4 text-muted-foreground transition-opacity",
          isAttached
            ? "opacity-0"
            : isHighlighted
              ? "opacity-100"
              : "opacity-0 group-hover/row:opacity-100",
        )}
      />
    </button>
  );
});
