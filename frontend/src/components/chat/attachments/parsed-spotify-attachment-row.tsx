import { forwardRef } from "react";
import { Plus } from "lucide-react";

import { cn } from "@/lib/utils";

import type { ParsedSpotifyRef } from "./spotify-id-parser";

type ParsedSpotifyAttachmentRowProps = {
  parsedRef: ParsedSpotifyRef;
  onPick: () => void;
  isHighlighted?: boolean;
  onMouseEnter?: () => void;
};

export const ParsedSpotifyAttachmentRow = forwardRef<
  HTMLButtonElement,
  ParsedSpotifyAttachmentRowProps
>(function ParsedSpotifyAttachmentRow(
  { parsedRef, onPick, isHighlighted = false, onMouseEnter },
  ref,
) {
  return (
    <button
      ref={ref}
      type="button"
      onClick={onPick}
      onMouseEnter={onMouseEnter}
      className={cn(
        "flex w-full items-center gap-2.5 rounded-md px-2 py-2 text-left transition-colors hover:bg-white/[0.05]",
        isHighlighted && "bg-white/[0.08]",
      )}
    >
      <div className="grid size-9 shrink-0 place-items-center rounded-[4px] bg-primary/15 text-primary ring-1 ring-primary/20">
        <Plus className="size-4" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-[13px] font-medium leading-tight">
          Spotify-{parsedRef.kind.replace("spotify-", "")} anhängen
        </p>
        <p className="mt-0.5 truncate text-[11px] text-muted-foreground">
          ID: {parsedRef.id}
        </p>
      </div>
    </button>
  );
});
