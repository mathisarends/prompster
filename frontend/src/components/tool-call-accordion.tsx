import { useState } from "react";
import { Check, ChevronDown, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export type ToolCallStatus = "pending" | "running" | "completed";

export type ToolCallItem = {
  id: string;
  text: string;
  status?: ToolCallStatus;
};

type ToolCallAccordionProps = {
  calls: ToolCallItem[];
  className?: string;
  defaultOpen?: boolean;
};

const getStatus = (call: ToolCallItem): ToolCallStatus =>
  call.status ?? "completed";

const HeaderIcon = ({ status }: { status: ToolCallStatus }) => {
  if (status === "running") {
    return (
      <span className="relative flex size-[18px] shrink-0 items-center justify-center">
        <span
          aria-hidden="true"
          className="absolute inset-0 animate-ping rounded-full bg-primary/20 opacity-70"
        />
        <Loader2 className="relative size-[18px] animate-spin text-primary" />
      </span>
    );
  }

  return (
    <span className="flex size-[18px] shrink-0 items-center justify-center rounded-full border border-primary/60 bg-primary/[0.07]">
      <Check className="size-[11px] text-primary" strokeWidth={3} />
    </span>
  );
};

const ChildMarker = ({ status }: { status: ToolCallStatus }) =>
  status === "running" ? (
    <Loader2 className="size-3 shrink-0 animate-spin text-primary" />
  ) : (
    <Check
      className="size-3 shrink-0 text-primary/70"
      strokeWidth={3}
    />
  );

export const ToolCallAccordion = ({
  calls,
  className,
  defaultOpen = false,
}: ToolCallAccordionProps) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  if (calls.length === 0) return null;

  const visibleCalls = calls.filter((call) => getStatus(call) !== "pending");
  const runningCall = calls.find((call) => getStatus(call) === "running");
  const isRunning = Boolean(runningCall);

  if (visibleCalls.length === 0) return null;

  const headerLabel = isRunning
    ? runningCall!.text
    : `${calls.length} ${
        calls.length === 1 ? "Tool verwendet" : "Tools verwendet"
      }`;

  return (
    <section
      className={cn("mt-3 text-sm", className)}
      aria-label="Tool-Aufrufe"
    >
      <button
        type="button"
        onClick={() => setIsOpen((current) => !current)}
        className="group flex w-full items-center gap-2.5 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40"
        aria-expanded={isOpen}
      >
        <HeaderIcon status={isRunning ? "running" : "completed"} />
        <span
          className={cn(
            "min-w-0 flex-1 truncate text-sm leading-6",
            isRunning
              ? "font-medium text-foreground"
              : "text-muted-foreground group-hover:text-foreground/90",
          )}
        >
          {headerLabel}
        </span>
        <ChevronDown
          className={cn(
            "size-4 shrink-0 text-muted-foreground/70 transition-transform duration-200",
            isOpen && "rotate-180",
          )}
        />
      </button>

      {isOpen && (
        <ul className="ml-[8px] mt-2.5 space-y-2 border-l border-white/10 pl-5">
          {visibleCalls.map((call) => {
            const status = getStatus(call);

            return (
              <li key={call.id} className="flex items-start gap-2">
                <span className="mt-[5px]">
                  <ChildMarker status={status} />
                </span>
                <span
                  className={cn(
                    "min-w-0 flex-1 break-words text-xs leading-5",
                    status === "running"
                      ? "font-medium text-foreground/90"
                      : "text-muted-foreground",
                  )}
                >
                  {call.text}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
};
