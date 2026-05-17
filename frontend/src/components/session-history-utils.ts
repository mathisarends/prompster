import type { SessionSummaryResponse } from "@/api/generated/model";

export type SessionHistoryGroup =
  | "Heute"
  | "Gestern"
  | "Letzte 7 Tage"
  | "Älter";

export type SessionHistoryEntry = SessionSummaryResponse & {
  group: SessionHistoryGroup;
};

const DAY_IN_MS = 24 * 60 * 60 * 1000;
const SESSION_GROUP_ORDER: SessionHistoryGroup[] = [
  "Heute",
  "Gestern",
  "Letzte 7 Tage",
  "Älter",
];

const getStartOfDay = (value: Date) =>
  new Date(value.getFullYear(), value.getMonth(), value.getDate());

export const getSessionHistoryGroup = (
  lastActivityAt: string,
  now: Date = new Date(),
): SessionHistoryGroup => {
  const parsedDate = new Date(lastActivityAt);
  if (Number.isNaN(parsedDate.getTime())) {
    return "Älter";
  }

  const dayDifference = Math.floor(
    (getStartOfDay(now).getTime() - getStartOfDay(parsedDate).getTime()) /
      DAY_IN_MS,
  );

  if (dayDifference <= 0) return "Heute";
  if (dayDifference === 1) return "Gestern";
  if (dayDifference <= 7) return "Letzte 7 Tage";
  return "Älter";
};

export const toSessionHistoryEntries = (
  sessions: SessionSummaryResponse[],
): SessionHistoryEntry[] => {
  return [...sessions]
    .sort(
      (left, right) =>
        new Date(right.last_activity_at).getTime() -
        new Date(left.last_activity_at).getTime(),
    )
    .map((session) => ({
      ...session,
      group: getSessionHistoryGroup(session.last_activity_at),
    }));
};

export const groupSessionHistoryEntries = (
  sessions: SessionSummaryResponse[],
): Array<{ group: SessionHistoryGroup; items: SessionHistoryEntry[] }> => {
  const grouped = new Map<SessionHistoryGroup, SessionHistoryEntry[]>();

  for (const entry of toSessionHistoryEntries(sessions)) {
    const group = grouped.get(entry.group);
    if (group) {
      group.push(entry);
      continue;
    }

    grouped.set(entry.group, [entry]);
  }

  return SESSION_GROUP_ORDER.flatMap((group) => {
    const items = grouped.get(group);
    if (!items || items.length === 0) {
      return [];
    }
    return [{ group, items }];
  });
};

export const formatSessionTimestamp = (value: string): string => {
  const parsedDate = new Date(value);
  if (Number.isNaN(parsedDate.getTime())) {
    return "";
  }

  const now = new Date();
  const today = getStartOfDay(now);
  const date = getStartOfDay(parsedDate);
  const dayDifference = Math.floor(
    (today.getTime() - date.getTime()) / DAY_IN_MS,
  );

  if (dayDifference <= 0) {
    return parsedDate.toLocaleTimeString("de-DE", {
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  if (parsedDate.getFullYear() === now.getFullYear()) {
    return parsedDate.toLocaleDateString("de-DE", {
      day: "2-digit",
      month: "2-digit",
    });
  }

  return parsedDate.toLocaleDateString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
};
