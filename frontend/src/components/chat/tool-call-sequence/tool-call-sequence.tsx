import { useState } from "react";
import { ChevronDown } from "lucide-react";

import { cn } from "@/lib/utils";

import { HeaderStatusIcon, TimelineIcon } from "./tool-call-sequence-icons";
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
        className="group flex w-full items-center gap-2.5 rounded-md py-1 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40"
        aria-expanded={isOpen}
      >
        <HeaderStatusIcon
          status={isRunning ? "running" : hasFailed ? "failed" : "completed"}
        />
        <span
          className={cn(
            "min-w-0 flex-1 truncate text-sm leading-5",
            isRunning
              ? "font-medium text-foreground"
              : hasFailed
                ? "font-medium text-destructive"
                : "text-foreground/80 group-hover:text-foreground",
          )}
        >
          {headerLabel}
        </span>
        <ChevronDown
          className={cn(
            "size-4 shrink-0 text-muted-foreground/50 transition-transform duration-200 group-hover:text-muted-foreground",
            isOpen && "rotate-180",
          )}
        />
      </button>

      {isOpen && (
        <ol className="mt-2 pl-[3px]">
          {calls.map((call, index) => {
            const status = getStatus(call);
            const isLast = index === calls.length - 1;

            return (
              <li
                key={call.id}
                className="relative flex items-start gap-3 pb-3 last:pb-0"
              >
                {!isLast && (
                  <span
                    aria-hidden="true"
                    className="absolute bottom-0 left-[7px] top-[22px] w-px bg-white/20"
                  />
                )}
                <span className="relative z-[1] mt-[3px] flex shrink-0">
                  <TimelineIcon call={call} status={status} />
                </span>
                <span
                  className={cn(
                    "block min-w-0 break-words text-[13px] leading-5",
                    status === "running"
                      ? "font-medium text-foreground"
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
