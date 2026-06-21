import { useEffect, useState } from "react";
import { ChevronRight, Play } from "lucide-react";

import { cn } from "@/shared/lib/utils";

import { TimelineIcon } from "./tool-call-sequence-icons";
import type {
  ToolCallAccordionProps,
  ToolCallItem,
  ToolCallStatus,
} from "./tool-call-sequence.types";

const SoundBars = () => (
  <span aria-hidden className="flex h-3.5 w-3.5 items-end justify-center gap-[2px]">
    <span className="sound-bar h-[70%] w-[2px] rounded-full bg-current [--sound-bar-high:1] [--sound-bar-low:0.35] [animation-delay:-0.12s] [animation-duration:0.72s]" />
    <span className="sound-bar h-full w-[2px] rounded-full bg-current [--sound-bar-high:0.86] [--sound-bar-low:0.18] [animation-delay:-0.44s] [animation-duration:0.94s]" />
    <span className="sound-bar h-[58%] w-[2px] rounded-full bg-current [--sound-bar-high:1] [--sound-bar-low:0.28] [animation-delay:-0.28s] [animation-duration:0.82s]" />
  </span>
);

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
  activeTrackUri,
  isPlaying = false,
  onToggleTrackPlayback,
}: ToolCallAccordionProps) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const [openCallIds, setOpenCallIds] = useState<Set<string>>(() => new Set());

  useEffect(() => {
    setOpenCallIds((current) => {
      const next = new Set(current);
      let changed = false;
      const expandableCallIds = new Set(getExpandableCallIds(calls));
      for (const callId of current) {
        if (expandableCallIds.has(callId)) continue;
        next.delete(callId);
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
                      "flex min-w-0 items-start gap-1.5 pt-[2px] text-left text-[13px] leading-5",
                      canExpand &&
                        "w-full rounded-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40",
                      !canExpand && "pointer-events-none",
                    )}
                    aria-expanded={canExpand ? isCallOpen : undefined}
                    tabIndex={canExpand ? 0 : -1}
                  >
                    {canExpand && (
                      <ChevronRight
                        aria-hidden="true"
                        className={cn(
                          "mt-[3px] size-3.5 shrink-0 text-muted-foreground/70 transition-transform",
                          isCallOpen && "rotate-90",
                        )}
                      />
                    )}
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
                          {call.resultItems.map((item, itemIndex) => {
                            const trackUri = item.trackUri ?? null;
                            const isPlayable = Boolean(
                              trackUri && onToggleTrackPlayback,
                            );
                            const isActive = Boolean(
                              trackUri &&
                                activeTrackUri &&
                                trackUri === activeTrackUri,
                            );
                            const isItemPlaying = isActive && isPlaying;

                            const cover = (
                              <span className="relative size-8 shrink-0 overflow-hidden rounded-sm bg-muted/60">
                                {item.coverUrl ? (
                                  <img
                                    src={item.coverUrl}
                                    alt=""
                                    className="size-full object-cover"
                                    loading="lazy"
                                  />
                                ) : null}
                                {isPlayable ? (
                                  <span
                                    className={cn(
                                      "absolute inset-0 grid place-items-center bg-black/55 text-white transition-opacity",
                                      isItemPlaying
                                        ? "opacity-100"
                                        : "opacity-0 group-hover/result:opacity-100",
                                    )}
                                  >
                                    {isItemPlaying ? (
                                      <SoundBars />
                                    ) : (
                                      <Play className="size-3.5 fill-current" />
                                    )}
                                  </span>
                                ) : null}
                              </span>
                            );

                            const label = (
                              <span className="flex min-w-0 flex-col">
                                {item.artist ? (
                                  <span className="min-w-0 truncate text-[11px] text-muted-foreground">
                                    {item.artist}
                                  </span>
                                ) : null}
                                <span
                                  className={cn(
                                    "min-w-0 truncate",
                                    isActive && "text-primary",
                                  )}
                                >
                                  {item.title}
                                </span>
                              </span>
                            );

                            return (
                              <li
                                key={`${call.id}-${item.title}-${itemIndex}`}
                                className="min-w-0 text-xs text-foreground/80"
                              >
                                {isPlayable && trackUri ? (
                                  <button
                                    type="button"
                                    onClick={() =>
                                      onToggleTrackPlayback?.({
                                        id: trackUri,
                                        title: item.title,
                                        artist: item.artist,
                                        coverUrl: item.coverUrl,
                                        spotifyUri: trackUri,
                                      })
                                    }
                                    aria-label={
                                      isItemPlaying
                                        ? `${item.title} pausieren`
                                        : `${item.title} abspielen`
                                    }
                                    className="group/result flex w-full min-w-0 items-center gap-2 rounded-sm py-0.5 text-left transition-colors hover:bg-white/[0.04] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40"
                                  >
                                    {cover}
                                    {label}
                                  </button>
                                ) : (
                                  <span className="flex min-w-0 items-center gap-2 py-0.5">
                                    {cover}
                                    {label}
                                  </span>
                                )}
                              </li>
                            );
                          })}
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
