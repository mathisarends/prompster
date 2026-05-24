import { Loader2, Plus } from "lucide-react";

import type { SpotifyTrackResponse } from "@/api/generated/model";
import { TrackCover } from "@/components/deck/search-panel/track-cover";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

type TrackResultRowProps = {
  track: SpotifyTrackResponse;
  isAdding: boolean;
  disabled: boolean;
  onAdd: () => void;
};

export const TrackResultRow = ({
  track,
  isAdding,
  disabled,
  onAdd,
}: TrackResultRowProps) => (
  <div className="grid grid-cols-[40px_minmax(0,1fr)_auto] items-center gap-3 rounded-md px-2 py-2 transition-colors hover:bg-white/[0.04]">
    <TrackCover src={track.coverUrl} alt={`${track.title} Cover`} />
    <div className="min-w-0">
      <p className="truncate text-sm font-semibold leading-tight">{track.title}</p>
      <p className="mt-0.5 truncate text-xs text-muted-foreground">
        {track.artist}
        {track.album ? ` · ${track.album}` : ""}
        {track.year ? ` · ${track.year}` : ""}
      </p>
    </div>
    <Tooltip>
      <TooltipTrigger
        render={
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            aria-label={`${track.title} hinzufügen`}
            disabled={disabled}
            onClick={onAdd}
          >
            {isAdding ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Plus className="size-4" />
            )}
          </Button>
        }
      />
      <TooltipContent side="left" sideOffset={8}>
        {track.title} hinzufügen
      </TooltipContent>
    </Tooltip>
  </div>
);