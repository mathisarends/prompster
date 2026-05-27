import {
  CircleAlert,
  Download,
  Loader2,
  MessageCircleQuestion,
  Search,
  Sparkles,
  Wrench,
} from "lucide-react";

import type {
  ToolCallItem,
  ToolCallStatus,
} from "./tool-call-sequence.types";

const renderActionIcon = (actionType: ToolCallItem["actionType"]) => {
  if (actionType === "search") {
    return (
      <Search
        className="size-[14px] shrink-0 text-muted-foreground/80"
        strokeWidth={2}
      />
    );
  }

  if (actionType === "fetch") {
    return (
      <Download
        className="size-[14px] shrink-0 text-muted-foreground/80"
        strokeWidth={2}
      />
    );
  }

  if (actionType === "mutate") {
    return (
      <Sparkles
        className="size-[14px] shrink-0 text-muted-foreground/80"
        strokeWidth={2}
      />
    );
  }

  if (actionType === "interact") {
    return (
      <MessageCircleQuestion
        className="size-[14px] shrink-0 text-muted-foreground/80"
        strokeWidth={2}
      />
    );
  }

  return (
    <Wrench
      className="size-[14px] shrink-0 text-muted-foreground/80"
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
      <Loader2 className="size-[14px] shrink-0 animate-spin text-primary" />
    );
  }

  if (status === "failed") {
    return (
      <CircleAlert
        className="size-[14px] shrink-0 text-destructive"
        strokeWidth={2.25}
      />
    );
  }

  return renderActionIcon(call.actionType);
};
