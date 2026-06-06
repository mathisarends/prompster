import { useState } from "react";

import { cn } from "@/shared/lib/utils";

import { TimelineIcon } from "./tool-call-sequence-icons";
import type {
  ToolCallAccordionProps,
  ToolCallItem,
  ToolCallStatus,
} from "./tool-call-sequence.types";

const getStatus = (call: ToolCallItem): ToolCallStatus =>
  call.status === "pending" ? "running" : (call.status ?? "completed");

export const ToolCallAccordion = ({
  calls,
  className,
  defaultOpen = false,
}: ToolCallAccordionProps) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  if (calls.length === 0) return null;

  const runningCall = [...calls]
    .reverse()
    .find((call) => getStatus(call) === "running");
  const failedCall = [...calls]
    .reverse()
    .find((call) => getStatus(call) === "failed");
  const isRunning = Boolean(runningCall);
  const hasFailed = Boolean(failedCall);

  const headerLabel = isRunning
    ? runningCall!.text
    : hasFailed
      ? `${failedCall!.text} fehlgeschlagen`
      : `${calls.length} ${
          calls.length === 1 ? "Tool verwendet" : "Tools verwendet"
        }`;

  return (
    <section
      className={cn("mt-3 text-sm", isOpen && "pb-3", className)}
      aria-label="Tool-Aufrufe"
    >
      <button
        type="button"
        onClick={() => setIsOpen((current) => !current)}
        className="group flex w-full items-center rounded-md py-1 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40"
        aria-expanded={isOpen}
      >
        <span
          className={cn(
            "min-w-0 flex-1 truncate text-sm leading-5",
            isRunning
              ? "chat-tool-running-text font-medium text-foreground"
              : hasFailed
                ? "font-medium text-destructive"
                : "text-foreground/80 group-hover:text-foreground",
          )}
        >
          {headerLabel}
        </span>
      </button>

      {isOpen && (
        <ol className="mt-2 pl-[3px]">
          {calls.map((call, index) => {
            const status = getStatus(call);
            const isLast = index === calls.length - 1;

            return (
              <li
                key={call.id}
                className="chat-tool-item relative flex items-start gap-3 pb-3 last:pb-0"
                style={{ animationDelay: `${Math.min(index * 60, 360)}ms` }}
              >
                {!isLast && (
                  <span
                    aria-hidden="true"
                    className={cn(
                      "absolute bottom-0 left-[10px] top-[26px] w-[2px] rounded-full chat-tool-connector",
                      status === "running"
                        ? "chat-tool-connector--running"
                        : status === "completed"
                          ? "chat-tool-connector--completed"
                          : status === "failed"
                            ? "chat-tool-connector--completed"
                            : undefined,
                    )}
                  />
                )}
                <span
                  aria-hidden="true"
                  className={cn(
                    "chat-tool-node relative z-[1] mt-[1px] shrink-0",
                    status === "running"
                      ? "chat-tool-node--running"
                      : status === "failed"
                        ? "chat-tool-node--failed"
                        : status === "completed"
                          ? "chat-tool-node--completed"
                          : undefined,
                  )}
                >
                  <TimelineIcon call={call} status={status} />
                </span>
                <span
                  className={cn(
                    "block min-w-0 break-words pt-[2px] text-[13px] leading-5",
                    status === "running"
                      ? "chat-tool-running-text font-medium"
                      : status === "failed"
                        ? "font-medium text-destructive"
                        : "text-muted-foreground",
                  )}
                >
                  {call.text}
                </span>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
};
