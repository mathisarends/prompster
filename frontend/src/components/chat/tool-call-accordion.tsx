import { useState } from "react";
import { Check, ChevronDown, CircleAlert, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export type ToolCallStatus = "pending" | "running" | "completed" | "failed";

export type ToolCallItem = {
  id: string;
  text: string;
  status?: ToolCallStatus;
  detail?: string;
};

type ToolCallAccordionProps = {
  calls: ToolCallItem[];
  className?: string;
  defaultOpen?: boolean;
};

const getStatus = (call: ToolCallItem): ToolCallStatus =>
  call.status === "pending" ? "running" : (call.status ?? "completed");

const HeaderIcon = ({ status }: { status: ToolCallStatus }) => {
  if (status === "running") {
    return (
      <span className="relative flex size-[22px] shrink-0 items-center justify-center">
        <span
          aria-hidden="true"
          className="absolute inset-0 animate-ping rounded-full bg-primary/20 opacity-70"
        />
        <Loader2 className="relative size-[18px] animate-spin text-primary" />
      </span>
    );
  }

  if (status === "failed") {
    return (
      <span className="flex size-[22px] shrink-0 items-center justify-center rounded-full border border-destructive/60 bg-destructive/[0.08]">
        <CircleAlert
          className="size-[12px] text-destructive"
          strokeWidth={2.5}
        />
      </span>
    );
  }

  return (
    <span className="flex size-[22px] shrink-0 items-center justify-center rounded-full border border-primary/50 bg-primary/[0.08]">
      <Check className="size-[12px] text-primary" strokeWidth={3} />
    </span>
  );
};

const ChildMarker = ({ status }: { status: ToolCallStatus }) =>
  status === "running" ? (
    <Loader2 className="size-3.5 shrink-0 animate-spin text-primary" />
  ) : status === "failed" ? (
    <CircleAlert
      className="size-3.5 shrink-0 text-destructive"
      strokeWidth={2.5}
    />
  ) : (
    <span
      aria-hidden="true"
      className="mt-[7px] size-1.5 shrink-0 rounded-full bg-primary/60"
    />
  );

export const ToolCallAccordion = ({
  calls,
  className,
  defaultOpen = false,
}: ToolCallAccordionProps) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  if (calls.length === 0) return null;

  const visibleCalls = calls;
  const runningCall = [...visibleCalls]
    .reverse()
    .find((call) => getStatus(call) === "running");
  const failedCall = [...visibleCalls]
    .reverse()
    .find((call) => getStatus(call) === "failed");
  const isRunning = Boolean(runningCall);
  const hasFailed = Boolean(failedCall);

  if (visibleCalls.length === 0) return null;

  const headerLabel = isRunning
    ? runningCall!.text
    : hasFailed
      ? `${failedCall!.text} fehlgeschlagen`
      : `${calls.length} ${
          calls.length === 1 ? "Tool verwendet" : "Tools verwendet"
        }`;

  return (
    <section
      className={cn(
        "mt-4 overflow-hidden rounded-2xl border border-white/[0.06] bg-card/40 text-sm backdrop-blur-sm",
        className,
      )}
      aria-label="Tool-Aufrufe"
    >
      <button
        type="button"
        onClick={() => setIsOpen((current) => !current)}
        className="group flex w-full items-center gap-3.5 px-5 py-4 text-left transition-colors hover:bg-white/[0.02] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40"
        aria-expanded={isOpen}
      >
        <HeaderIcon
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
            "size-4 shrink-0 text-muted-foreground/60 transition-transform duration-200 group-hover:text-muted-foreground",
            isOpen && "rotate-180",
          )}
        />
      </button>

      {isOpen && (
        <div className="px-5 pb-5">
          <div className="mb-4 h-px w-full bg-white/[0.06]" />
          <ul className="space-y-3.5 pl-[6px]">
            {visibleCalls.map((call) => {
              const status = getStatus(call);

              return (
                <li key={call.id} className="flex items-start gap-3">
                  <ChildMarker status={status} />
                  <span
                    className={cn(
                      "block min-w-0 break-words text-[13px] leading-5",
                      status === "running"
                        ? "font-medium text-foreground/90"
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
          </ul>
        </div>
      )}
    </section>
  );
};
