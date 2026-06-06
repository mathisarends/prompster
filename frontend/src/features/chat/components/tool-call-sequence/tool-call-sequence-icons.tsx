import {
  CircleAlert,
  Download,
  Loader2,
  MessageCircle,
  Plus,
  RefreshCw,
  Search,
  Trash2,
  Wrench,
} from "lucide-react";

import type { ToolCallItem, ToolCallStatus } from "./tool-call-sequence.types";

const renderActionIcon = (actionType: ToolCallItem["actionType"]) => {
  if (actionType === "search_tracks" || actionType === "search_playlists") {
    return (
      <Search
        className="size-[13px] shrink-0 text-foreground/65"
        strokeWidth={2}
      />
    );
  }

  if (actionType === "get_spotify_playlist_tracks") {
    return (
      <Download
        className="size-[13px] shrink-0 text-foreground/65"
        strokeWidth={2}
      />
    );
  }

  if (actionType === "add_deck_tracks") {
    return (
      <Plus
        className="size-[13px] shrink-0 text-foreground/65"
        strokeWidth={2}
      />
    );
  }

  if (actionType === "remove_deck_tracks") {
    return (
      <Trash2
        className="size-[13px] shrink-0 text-foreground/65"
        strokeWidth={2}
      />
    );
  }

  if (actionType === "replace_deck_tracks") {
    return (
      <RefreshCw
        className="size-[13px] shrink-0 text-foreground/65"
        strokeWidth={2}
      />
    );
  }

  if (actionType === "self_review") {
    return (
      <MessageCircle
        className="size-[13px] shrink-0 text-foreground/65"
        strokeWidth={2}
      />
    );
  }

  if (actionType === "ask_onboarding_question") {
    return (
      <Wrench
        className="size-[13px] shrink-0 text-foreground/65"
        strokeWidth={2}
      />
    );
  }

  return (
    <Wrench
      className="size-[13px] shrink-0 text-foreground/65"
      strokeWidth={2}
    />
  );
};

export const TimelineIcon = ({
  call,
  status,
}: {
  call: ToolCallItem;
  status: ToolCallStatus;
}) => {
  if (status === "running") {
    return (
      <Loader2 className="size-[13px] shrink-0 animate-spin text-primary" />
    );
  }

  if (status === "failed") {
    return (
      <CircleAlert
        className="size-[13px] shrink-0 text-destructive"
        strokeWidth={2.25}
      />
    );
  }

  return renderActionIcon(call.actionType);
};
