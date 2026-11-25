import type { ToolCallProgress } from "../types";
import type { ChatEntry } from "./chat-reducer";

/**
 * The conversation as far as the presentation of the agent's work has come.
 *
 * Calls the presentation has yet to reach are left out, the one it is showing
 * counts as still running, and everything after them waits. `behind` tells
 * that something is held back.
 */
export function followProgress(
  entries: ChatEntry[],
  progress: ToolCallProgress | null,
): { entries: ChatEntry[]; behind: boolean } {
  if (!progress) {
    return { entries, behind: false };
  }
  const shown: ChatEntry[] = [];
  for (const entry of entries) {
    if (entry.kind !== "tool_call_group") {
      shown.push(entry);
      continue;
    }
    const reached = entry.calls.filter((call) => !progress.waiting.has(call.id));
    const working = reached.some((call) => call.id === progress.working);
    if (reached.length === entry.calls.length && !working) {
      shown.push(entry);
      continue;
    }
    if (reached.length) {
      shown.push({
        ...entry,
        calls: reached.map((call) =>
          call.id === progress.working ? { ...call, state: "pending", resultItems: [] } : call,
        ),
      });
    }
    return { entries: shown, behind: true };
  }
  return { entries: shown, behind: false };
}
