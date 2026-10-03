import type { SessionSummaryResponse } from "@/api/generated/model";

export type SessionHistoryEntry = SessionSummaryResponse & {
  group: string;
};

const getHistoryGroup = (lastActivityAt: string, today: Date): string => {
  const activity = new Date(lastActivityAt);
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const lastWeek = new Date(today);
  lastWeek.setDate(lastWeek.getDate() - 7);
  const lastMonth = new Date(today);
  lastMonth.setDate(lastMonth.getDate() - 30);

  if (activity >= today) return "Heute";
  if (activity >= yesterday) return "Gestern";
  if (activity >= lastWeek) return "Letzte 7 Tage";
  if (activity >= lastMonth) return "Letzte 30 Tage";
  return "Älter";
};

export const toSessionHistoryEntries = (
  sessions: readonly SessionSummaryResponse[],
): SessionHistoryEntry[] => {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return sessions.map((session) => ({
    ...session,
    group: getHistoryGroup(session.lastActivityAt, today),
  }));
};
