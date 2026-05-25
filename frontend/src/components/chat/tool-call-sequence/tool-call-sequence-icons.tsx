import {
  Check,
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

export const HeaderStatusIcon = ({ status }: { status: ToolCallStatus }) => {
  if (status === "running") {
    return (
      <span className="relative flex size-[18px] shrink-0 items-center justify-center">
        <span
          aria-hidden="true"
          className="absolute inset-0 animate-ping rounded-full bg-primary/25 opacity-70"
        />
        <Loader2 className="relative size-[14px] animate-spin text-primary" />
      </span>
    );
  }

  if (status === "failed") {
    return (
      <CircleAlert
        className="size-[16px] shrink-0 text-destructive"
        strokeWidth={2.25}
      />
    );
  }

  return (
    <span className="flex size-[16px] shrink-0 items-center justify-center rounded-full border border-primary/50 bg-primary/[0.08]">
      <Check className="size-[10px] text-primary" strokeWidth={3} />
    </span>
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
