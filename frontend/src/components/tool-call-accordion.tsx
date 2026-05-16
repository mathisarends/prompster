import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

export type ToolCallItem = {
  id: string;
  text: string;
  details?: string[];
};

type ToolCallAccordionProps = {
  calls: ToolCallItem[];
  className?: string;
  defaultOpen?: boolean;
};

export const ToolCallAccordion = ({
  calls,
  className,
  defaultOpen = false,
}: ToolCallAccordionProps) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const [openCallIds, setOpenCallIds] = useState<Set<string>>(() => new Set());

  if (calls.length === 0) return null;

  const toggleCall = (id: string) => {
    setOpenCallIds((currentIds) => {
      const nextIds = new Set(currentIds);

      if (nextIds.has(id)) {
        nextIds.delete(id);
      } else {
        nextIds.add(id);
      }

      return nextIds;
    });
  };

  return (
    <section
      className={cn("mt-2 text-sm text-muted-foreground", className)}
      aria-label="Ausgeführte Tools"
    >
      <button
        type="button"
        onClick={() => setIsOpen((current) => !current)}
        className="inline-flex items-center gap-1.5 text-left text-xs font-medium text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
        aria-expanded={isOpen}
      >
        <span>
          {calls.length} {calls.length === 1 ? "Tool-Aufruf" : "Tool-Aufrufe"}
        </span>
        <ChevronDown
          className={cn(
            "size-3.5 shrink-0 transition-transform duration-200",
            isOpen && "rotate-180",
          )}
        />
      </button>

      {isOpen && (
        <div className="mt-2 space-y-1">
          {calls.map((call) => {
            const isCallOpen = openCallIds.has(call.id);
            const hasDetails = Boolean(call.details && call.details.length > 0);

            return (
              <div key={call.id} className="pl-1">
                <button
                  type="button"
                  onClick={() => hasDetails && toggleCall(call.id)}
                  className={cn(
                    "inline-flex min-h-6 items-start gap-2 text-left text-sm leading-6 text-foreground/85 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50",
                    hasDetails && "hover:text-foreground",
                  )}
                  aria-expanded={hasDetails ? isCallOpen : undefined}
                >
                  <span className="mt-[2px] text-muted-foreground">-</span>
                  <span className="min-w-0 flex-1">
                    <span className="block break-words">{call.text}</span>
                  </span>
                  {hasDetails && (
                    <ChevronDown
                      className={cn(
                        "mt-1 size-3.5 shrink-0 text-muted-foreground transition-transform duration-200",
                        isCallOpen && "rotate-180",
                      )}
                    />
                  )}
                </button>

                {isCallOpen && hasDetails && (
                  <div className="ml-4 mt-1 space-y-1 border-l border-white/10 pl-3">
                    {call.details?.map((detail) => (
                      <p
                        key={`${call.id}-${detail}`}
                        className="break-words text-xs leading-5 text-muted-foreground"
                      >
                        {detail}
                      </p>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
};
