import type {
  ToolCallActionType,
  ToolCallItem,
  ToolCallStatus,
} from "@/features/chat/types";
import type { PlayableTrackInput } from "@/features/deck/hooks/useDeckPlayerController";

export type { ToolCallActionType, ToolCallItem, ToolCallStatus };

export type ToolCallAccordionProps = {
  calls: ToolCallItem[];
  className?: string;
  defaultOpen?: boolean;
  activeTrackUri?: string | null;
  isPlaying?: boolean;
  onToggleTrackPlayback?: (track: PlayableTrackInput) => void;
};
