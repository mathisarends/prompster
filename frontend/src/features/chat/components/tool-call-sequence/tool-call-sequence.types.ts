import type {
  ToolCallActionType,
  ToolCallItem,
  ToolCallSequenceLabel,
  ToolCallStatus,
} from "@/features/chat/types";
import type { PlayableTrackInput } from "@/features/deck/hooks/useDeckPlayerController";

export type { ToolCallActionType, ToolCallItem, ToolCallStatus };

export type ToolCallAccordionProps = {
  calls: ToolCallItem[];
  label?: ToolCallSequenceLabel;
  isActive?: boolean;
  className?: string;
  defaultOpen?: boolean;
  activeTrackUri?: string | null;
  isPlaying?: boolean;
  onToggleTrackPlayback?: (track: PlayableTrackInput) => void;
  addingSpotifyTrackUri?: string | null;
  onAddSpotifyTrack?: (spotifyUri: string) => Promise<void> | void;
};
