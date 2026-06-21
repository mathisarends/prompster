import { useEffect, useState } from "react";

import { cn } from "@/shared/lib/utils";

import { TimelineIcon } from "./tool-call-sequence-icons";
import type {
  ToolCallAccordionProps,
  ToolCallItem,
  ToolCallStatus,
} from "./tool-call-sequence.types";

const getStatus = (call: ToolCallItem): ToolCallStatus =>
  call.status === "pending" ? "running" : (call.status ?? "completed");

const hasExpandableDetail = (call: ToolCallItem) =>
  Boolean(call.resultItems?.length);

const getExpandableCallIds = (calls: ToolCallItem[]) =>
  calls
    .filter((call) => hasExpandableDetail(call))
    .map((call) => call.id);

export const ToolCallAccordion = ({
  calls,
  className,
  defaultOpen = false,
}: ToolCallAccordionProps) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const [openCallIds, setOpenCallIds] = useState<Set<string>>(
    () => new Set(getExpandableCallIds(calls)),
  );

  useEffect(() => {
    setOpenCallIds((current) => {
      const next = new Set(current);
      let changed = false;
      for (const callId of getExpandableCallIds(calls)) {
        if (next.has(callId)) continue;
        next.add(callId);
        changed = true;
      }
      return changed ? next : current;
    });
  }, [calls]);

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

  const toggleCall = (callId: string) => {
    setOpenCallIds((current) => {
      const next = new Set(current);
      if (next.has(callId)) {
        next.delete(callId);
      } else {
        next.add(callId);
      }
      return next;
    });
  };

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
            const canExpand = hasExpandableDetail(call);
            const isCallOpen = openCallIds.has(call.id);

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
                <span className="min-w-0 flex-1">
                  <button
                    type="button"
                    onClick={canExpand ? () => toggleCall(call.id) : undefined}
                    className={cn(
                      "flex min-w-0 items-start pt-[2px] text-left text-[13px] leading-5",
                      canExpand &&
                        "w-full rounded-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40",
                      !canExpand && "pointer-events-none",
                    )}
                    aria-expanded={canExpand ? isCallOpen : undefined}
                    tabIndex={canExpand ? 0 : -1}
                  >
                    <span
                      className={cn(
                        "block min-w-0 break-words",
                        status === "running"
                          ? "chat-tool-running-text font-medium"
                          : status === "failed"
                            ? "font-medium text-destructive"
                            : "text-muted-foreground",
                      )}
                    >
                      {call.text}
                    </span>
                  </button>
                  {canExpand && isCallOpen && (
                    <div className="mt-2 pl-5">
                      {call.resultItems && call.resultItems.length > 0 && (
                        <ul className="chat-tool-result-list grid max-h-[11.625rem] gap-1.5 overflow-y-auto pr-2">
                          {call.resultItems.map((item, itemIndex) => (
                            <li
                              key={`${call.id}-${item.title}-${itemIndex}`}
                              className="flex h-9 min-w-0 items-center gap-2 text-xs text-foreground/80"
                            >
                              {item.coverUrl ? (
                                <img
                                  src={item.coverUrl}
                                  alt=""
                                  className="size-7 shrink-0 rounded-sm object-cover"
                                  loading="lazy"
                                />
                              ) : (
                                <span className="size-7 shrink-0 rounded-sm bg-muted/60" />
                              )}
                              <span className="min-w-0 truncate">
                                {item.title}
                              </span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}
                </span>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
};
