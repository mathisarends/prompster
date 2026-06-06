import { useMutation, useQueryClient } from "@tanstack/react-query";

import type { SessionSummaryResponse } from "@/api/generated/model";
import {
  getGetSessionQueryKey,
  getListSessionsQueryKey,
  starSession,
  unstarSession,
} from "@/api/generated/session-api";

export const useSessionStarActions = () => {
  const queryClient = useQueryClient();

  const invalidate = async (sessionId: string) => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: getListSessionsQueryKey() }),
      queryClient.invalidateQueries({
        queryKey: getGetSessionQueryKey(sessionId),
      }),
    ]);
  };

  const starMutation = useMutation({
    mutationFn: (sessionId: string) => starSession(sessionId),
    onSuccess: (_data, sessionId) => invalidate(sessionId),
  });
  const unstarMutation = useMutation({
    mutationFn: (sessionId: string) => unstarSession(sessionId),
    onSuccess: (_data, sessionId) => invalidate(sessionId),
  });

  const isTogglingFor = (sessionId: string) =>
    (starMutation.isPending && starMutation.variables === sessionId) ||
    (unstarMutation.isPending && unstarMutation.variables === sessionId);

  const toggleStar = (
    session: Pick<SessionSummaryResponse, "id" | "isStarred">,
  ) => {
    if (session.isStarred) {
      if (unstarMutation.isPending) return;
      unstarMutation.mutate(session.id);
      return;
    }
    if (starMutation.isPending) return;
    starMutation.mutate(session.id);
  };

  return { toggleStar, isTogglingFor };
};
